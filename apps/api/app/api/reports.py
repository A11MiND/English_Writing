from __future__ import annotations

import csv
from collections import Counter
from io import StringIO
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import Role, require_roles, write_audit_log
from app.core.database import get_session
from app.core.responses import ApiException, ErrorCode, success_response
from app.models import (
    Assignment,
    AuditLog,
    Class,
    ClassMembership,
    ClassReport,
    MarkingResult,
    Rubric,
    School,
    StudentProfile,
    Submission,
    TeacherReview,
    User,
    WritingTask,
    utc_now,
)
from app.services.marking import rubric_score_limits, rubric_total_score

router = APIRouter(prefix="/api", tags=["reports"])


async def require_teacher_class(db: AsyncSession, teacher: User, class_id: str) -> Class:
    result = await db.execute(
        select(Class)
        .join(ClassMembership, ClassMembership.class_id == Class.id)
        .where(
            Class.id == class_id,
            Class.school_id == teacher.school_id,
            ClassMembership.school_id == teacher.school_id,
            ClassMembership.user_id == teacher.id,
            ClassMembership.membership_role == Role.TEACHER,
        )
    )
    class_row = result.scalar_one_or_none()
    if class_row is None:
        raise ApiException(ErrorCode.ACCESS_DENIED, "Class is not assigned to this teacher.", 403)
    return class_row


def score_distribution_labels(maximum_score: int | None) -> list[str]:
    if maximum_score is None:
        return ["0-33%", "34-66%", "67-100%", "100%+", "unscored"]
    first_end = maximum_score // 3
    second_end = (maximum_score * 2) // 3
    return [
        f"0-{first_end}",
        f"{first_end + 1}-{second_end}",
        f"{second_end + 1}-{maximum_score}",
        f"{maximum_score + 1}+",
        "unscored",
    ]


def score_bucket(
    score: int | None,
    score_maximum: int,
    distribution_maximum: int | None,
) -> str:
    if score is None:
        return "unscored"
    if distribution_maximum is None:
        ratio = score / score_maximum
        if ratio <= 1 / 3:
            return "0-33%"
        if ratio <= 2 / 3:
            return "34-66%"
        if ratio <= 1:
            return "67-100%"
        return "100%+"
    first_end = distribution_maximum // 3
    second_end = (distribution_maximum * 2) // 3
    if score <= first_end:
        return f"0-{first_end}"
    if score <= second_end:
        return f"{first_end + 1}-{second_end}"
    if score <= distribution_maximum:
        return f"{second_end + 1}-{distribution_maximum}"
    return f"{distribution_maximum + 1}+"


def summarize_scores(
    values: list[tuple[int, int]], common_maximum: int | None
) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    raw_average = (
        round(sum(score for score, _ in values) / len(values), 2)
        if common_maximum is not None
        else None
    )
    percentage_average = round(
        sum((score / maximum) * 100 for score, maximum in values) / len(values),
        2,
    )
    return raw_average, percentage_average


def score_from_review_or_ai(
    review: TeacherReview | None, marking_result: MarkingResult | None
) -> tuple[int | None, int | None, int | None, int | None]:
    if review and review.total_score is not None:
        return (
            review.content_score,
            review.language_score,
            review.organisation_score,
            review.total_score,
        )
    if marking_result and marking_result.total_score is not None:
        return (
            marking_result.content_score,
            marking_result.language_score,
            marking_result.organisation_score,
            marking_result.total_score,
        )
    return (None, None, None, None)


async def build_class_report_payload(
    db: AsyncSession, teacher: User, class_id: str, task_id: str | None = None
) -> dict:
    class_row = await require_teacher_class(db, teacher, class_id)
    school_result = await db.execute(select(School).where(School.id == teacher.school_id))
    school = school_result.scalar_one_or_none()

    task_statement = (
        select(WritingTask)
        .join(Assignment, Assignment.task_id == WritingTask.id)
        .options(selectinload(WritingTask.rubric).selectinload(Rubric.dimensions))
        .where(
            Assignment.school_id == teacher.school_id,
            Assignment.class_id == class_id,
            WritingTask.school_id == teacher.school_id,
        )
        .order_by(WritingTask.created_at.desc())
    )
    if task_id:
        task_statement = task_statement.where(WritingTask.id == task_id)
    tasks = list((await db.execute(task_statement)).scalars().all())
    if task_id and not tasks:
        raise ApiException(ErrorCode.NOT_FOUND, "Task report scope not found.", 404)

    student_result = await db.execute(
        select(User, StudentProfile)
        .join(ClassMembership, ClassMembership.user_id == User.id)
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .where(
            User.school_id == teacher.school_id,
            StudentProfile.school_id == teacher.school_id,
            ClassMembership.school_id == teacher.school_id,
            ClassMembership.class_id == class_id,
            ClassMembership.membership_role == Role.STUDENT,
        )
        .order_by(User.display_name)
    )
    students = list(student_result.all())
    student_ids = [student.id for student, _ in students]
    task_ids = [task.id for task in tasks]

    submissions_by_key: dict[tuple[str, str], Submission] = {}
    if student_ids and task_ids:
        submission_result = await db.execute(
            select(Submission).where(
                Submission.school_id == teacher.school_id,
                Submission.student_id.in_(student_ids),
                Submission.task_id.in_(task_ids),
            )
        )
        submissions_by_key = {
            (submission.student_id, submission.task_id): submission
            for submission in submission_result.scalars().all()
        }

    submission_ids = [submission.id for submission in submissions_by_key.values()]
    marking_by_submission: dict[str, MarkingResult] = {}
    review_by_submission: dict[str, TeacherReview] = {}
    if submission_ids:
        marking_result = await db.execute(
            select(MarkingResult).where(
                MarkingResult.school_id == teacher.school_id,
                MarkingResult.submission_id.in_(submission_ids),
            )
        )
        marking_by_submission = {
            marking.submission_id: marking for marking in marking_result.scalars().all()
        }
        review_result = await db.execute(
            select(TeacherReview).where(
                TeacherReview.school_id == teacher.school_id,
                TeacherReview.submission_id.in_(submission_ids),
            )
        )
        review_by_submission = {review.submission_id: review for review in review_result.scalars().all()}

    score_limits_by_task = {
        task.id: rubric_score_limits(task.rubric.dimensions) for task in tasks
    }
    total_maximum_by_task = {
        task.id: rubric_total_score(score_limits_by_task[task.id]) for task in tasks
    }
    total_maxima = set(total_maximum_by_task.values())
    distribution_maximum = next(iter(total_maxima)) if len(total_maxima) == 1 else None

    completion_rows: list[dict] = []
    score_values: list[tuple[int, int]] = []
    content_scores: list[tuple[int, int]] = []
    language_scores: list[tuple[int, int]] = []
    organisation_scores: list[tuple[int, int]] = []
    distribution = Counter(
        {label: 0 for label in score_distribution_labels(distribution_maximum)}
    )
    weakness_counts: Counter[str] = Counter()

    for student, profile in students:
        for task in tasks:
            score_limits = score_limits_by_task[task.id]
            content_maximum = int(score_limits["content_score"]["max_score"])
            language_maximum = int(score_limits["language_score"]["max_score"])
            organisation_maximum = int(score_limits["organisation_score"]["max_score"])
            total_maximum = total_maximum_by_task[task.id]
            submission = submissions_by_key.get((student.id, task.id))
            marking = marking_by_submission.get(submission.id) if submission else None
            review = review_by_submission.get(submission.id) if submission else None
            content, language, organisation, total = score_from_review_or_ai(review, marking)
            distribution[
                score_bucket(total, total_maximum, distribution_maximum)
            ] += 1
            if total is not None:
                score_values.append((total, total_maximum))
            if content is not None:
                content_scores.append((content, content_maximum))
            if language is not None:
                language_scores.append((language, language_maximum))
            if organisation is not None:
                organisation_scores.append((organisation, organisation_maximum))
            if marking:
                for weakness in marking.weaknesses:
                    if isinstance(weakness, str) and weakness.strip():
                        weakness_counts[weakness.strip()] += 1
            completion_rows.append(
                {
                    "student_id": student.id,
                    "student_name": student.display_name,
                    "student_number": profile.student_number,
                    "task_id": task.id,
                    "task_title": task.title,
                    "mode": task.mode,
                    "submitted": submission is not None,
                    "submitted_at": submission.submitted_at.isoformat() if submission else None,
                    "word_count": submission.word_count if submission else None,
                    "content_score": content,
                    "language_score": language,
                    "organisation_score": organisation,
                    "total_score": total,
                    "content_max_score": content_maximum,
                    "language_max_score": language_maximum,
                    "organisation_max_score": organisation_maximum,
                    "total_max_score": total_maximum,
                    "rubric_id": task.rubric.id,
                    "rubric_title": task.rubric.title,
                    "review_status": review.status if review else None,
                    "marking_status": marking.status if marking else None,
                }
            )

    expected_submissions = len(students) * len(tasks)
    submitted_count = sum(1 for row in completion_rows if row["submitted"])
    average_total, average_total_percentage = summarize_scores(
        score_values, distribution_maximum
    )
    content_maxima = {
        int(limits["content_score"]["max_score"])
        for limits in score_limits_by_task.values()
    }
    language_maxima = {
        int(limits["language_score"]["max_score"])
        for limits in score_limits_by_task.values()
    }
    organisation_maxima = {
        int(limits["organisation_score"]["max_score"])
        for limits in score_limits_by_task.values()
    }
    common_content_maximum = (
        next(iter(content_maxima)) if len(content_maxima) == 1 else None
    )
    common_language_maximum = (
        next(iter(language_maxima)) if len(language_maxima) == 1 else None
    )
    common_organisation_maximum = (
        next(iter(organisation_maxima)) if len(organisation_maxima) == 1 else None
    )
    content_average, content_average_percentage = summarize_scores(
        content_scores, common_content_maximum
    )
    language_average, language_average_percentage = summarize_scores(
        language_scores, common_language_maximum
    )
    organisation_average, organisation_average_percentage = summarize_scores(
        organisation_scores, common_organisation_maximum
    )
    rubric_breakdown = {
        "content_average": content_average,
        "content_average_percentage": content_average_percentage,
        "content_max_score": common_content_maximum,
        "language_average": language_average,
        "language_average_percentage": language_average_percentage,
        "language_max_score": common_language_maximum,
        "organisation_average": organisation_average,
        "organisation_average_percentage": organisation_average_percentage,
        "organisation_max_score": common_organisation_maximum,
    }

    latest_report = await db.execute(
        select(ClassReport)
        .where(
            ClassReport.school_id == teacher.school_id,
            ClassReport.class_id == class_id,
            ClassReport.task_id == task_id,
        )
        .order_by(desc(ClassReport.generated_at))
        .limit(1)
    )
    latest = latest_report.scalar_one_or_none()

    return {
        "class_report": {
            "id": latest.id if latest else None,
            "school_name": school.name if school else "W F Joseph Lee Primary School",
            "class_id": class_row.id,
            "class_name": class_row.name,
            "level": class_row.level,
            "task_id": task_id,
            "generated_at": latest.generated_at.isoformat() if latest else None,
            "status": latest.status if latest else "LIVE_PREVIEW",
        },
        "summary": {
            "student_count": len(students),
            "assigned_task_count": len(tasks),
            "expected_submissions": expected_submissions,
            "submitted_count": submitted_count,
            "completion_rate": round(submitted_count / expected_submissions, 4)
            if expected_submissions
            else 0,
            "scored_submission_count": len(score_values),
            "average_total_score": average_total,
            "average_total_percentage": average_total_percentage,
            "maximum_total_score": distribution_maximum,
        },
        "rubric_breakdown": rubric_breakdown,
        "score_distribution": dict(distribution),
        "common_weaknesses": [
            {"weakness": weakness, "count": count}
            for weakness, count in weakness_counts.most_common(10)
        ],
        "completion_rows": completion_rows,
    }


@router.get("/teacher/reports/classes/{class_id}")
async def get_teacher_class_report(
    class_id: str,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
    task_id: Annotated[str | None, Query()] = None,
) -> dict:
    payload = await build_class_report_payload(db, user, class_id, task_id)
    return success_response(request, payload)


@router.post("/teacher/reports/classes/{class_id}/generate")
async def generate_teacher_class_report(
    class_id: str,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
    task_id: Annotated[str | None, Query()] = None,
) -> dict:
    payload = await build_class_report_payload(db, user, class_id, task_id)
    row = ClassReport(
        school_id=user.school_id or "",
        class_id=class_id,
        task_id=task_id,
        generated_by=user.id,
        status="READY",
        summary=payload,
        generated_at=utc_now(),
    )
    db.add(row)
    await write_audit_log(
        db,
        request,
        "CLASS_REPORT_GENERATED",
        user,
        {"class_id": class_id, "task_id": task_id},
    )
    await db.commit()
    await db.refresh(row)
    payload["class_report"]["id"] = row.id
    payload["class_report"]["generated_at"] = row.generated_at.isoformat()
    payload["class_report"]["status"] = row.status
    return success_response(request, payload)


def class_report_to_csv(payload: dict) -> str:
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "student_number",
            "student_name",
            "task_title",
            "mode",
            "submitted",
            "submitted_at",
            "word_count",
            "content_score",
            "content_max_score",
            "language_score",
            "language_max_score",
            "organisation_score",
            "organisation_max_score",
            "total_score",
            "total_max_score",
            "rubric_title",
            "review_status",
            "marking_status",
        ],
    )
    writer.writeheader()
    for row in payload["completion_rows"]:
        writer.writerow({field: sanitize_csv_cell(row.get(field)) for field in writer.fieldnames})
    return output.getvalue()


def sanitize_csv_cell(value: object) -> object:
    if not isinstance(value, str):
        return value
    if value and value[0] in {"=", "+", "-", "@", "\t", "\r", "\n"}:
        return f"'{value}"
    return value


PDF_NAVY = (0.09, 0.16, 0.29)
PDF_PURPLE = (0.45, 0.35, 0.78)
PDF_CORAL = (0.94, 0.35, 0.26)
PDF_SAGE = (0.43, 0.59, 0.36)
PDF_AMBER = (0.86, 0.58, 0.18)
PDF_INK = (0.25, 0.27, 0.32)
PDF_MUTED = (0.44, 0.42, 0.44)
PDF_BORDER = (0.87, 0.84, 0.78)
PDF_IVORY = (1.0, 0.996, 0.98)
PDF_LAVENDER = (0.95, 0.93, 0.98)


def pdf_escape(value: object) -> str:
    text = str(value if value is not None else "-")
    safe_text = text.encode("latin-1", "replace").decode("latin-1")
    return safe_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_colour(colour: tuple[float, float, float]) -> str:
    return " ".join(f"{channel:.3f}" for channel in colour)


def pdf_text(
    commands: list[str],
    x: float,
    y: float,
    text: object,
    *,
    size: float = 10,
    bold: bool = False,
    colour: tuple[float, float, float] = PDF_INK,
) -> None:
    font = "F2" if bold else "F1"
    commands.append(
        f"BT /{font} {size:.1f} Tf {pdf_colour(colour)} rg {x:.1f} {y:.1f} Td "
        f"({pdf_escape(text)}) Tj ET"
    )


def pdf_rect(
    commands: list[str],
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    fill: tuple[float, float, float],
    stroke: tuple[float, float, float] | None = None,
) -> None:
    if stroke:
        commands.append(
            f"q {pdf_colour(fill)} rg {pdf_colour(stroke)} RG {x:.1f} {y:.1f} "
            f"{width:.1f} {height:.1f} re B Q"
        )
    else:
        commands.append(
            f"q {pdf_colour(fill)} rg {x:.1f} {y:.1f} {width:.1f} {height:.1f} re f Q"
        )


def pdf_line(
    commands: list[str],
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    colour: tuple[float, float, float] = PDF_BORDER,
) -> None:
    commands.append(
        f"q {pdf_colour(colour)} RG 0.6 w {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S Q"
    )


def build_pdf_document(page_commands: list[list[str]]) -> bytes:
    page_count = len(page_commands)
    object_count = 4 + (page_count * 2)
    page_objects = [5 + (index * 2) for index in range(page_count)]
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            f"<< /Type /Pages /Kids [{' '.join(f'{number} 0 R' for number in page_objects)}] "
            f"/Count {page_count} >>"
        ).encode("ascii"),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    }
    for index, commands in enumerate(page_commands):
        page_object = 5 + (index * 2)
        stream_object = page_object + 1
        stream = "\n".join(commands).encode("latin-1", "replace")
        objects[page_object] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {stream_object} 0 R >>"
        ).encode("ascii")
        objects[stream_object] = (
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (object_count + 1)
    for object_number in range(1, object_count + 1):
        offsets[object_number] = len(pdf)
        pdf.extend(f"{object_number} 0 obj\n".encode("ascii"))
        pdf.extend(objects[object_number])
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {object_count + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer << /Size {object_count + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def build_class_report_pdf(payload: dict, generated_at: str) -> bytes:
    report = payload["class_report"]
    summary = payload["summary"]
    rubric = payload["rubric_breakdown"]
    weaknesses = payload["common_weaknesses"]
    rows = payload["completion_rows"]
    scope = rows[0]["task_title"] if report["task_id"] and rows else "All assigned writing"
    average_total = summary["average_total_score"]
    maximum_total = summary["maximum_total_score"]
    average_percentage = summary["average_total_percentage"]
    if average_total is not None and maximum_total is not None:
        average_score_label = f"{average_total} / {maximum_total}"
    elif average_percentage is not None:
        average_score_label = f"{average_percentage}%"
    else:
        average_score_label = "-"

    overview: list[str] = []
    pdf_rect(overview, 0, 0, 595, 842, fill=PDF_IVORY)
    pdf_rect(overview, 0, 720, 595, 122, fill=PDF_NAVY)
    pdf_text(overview, 42, 800, "English AI Writing Platform", size=11, bold=True, colour=(1, 1, 1))
    pdf_text(overview, 42, 765, "Class writing report", size=27, bold=True, colour=(1, 1, 1))
    pdf_text(overview, 42, 744, report["school_name"], size=10, colour=(0.83, 0.86, 0.92))
    pdf_text(overview, 470, 783, report["class_name"], size=18, bold=True, colour=(1, 1, 1))
    pdf_text(overview, 470, 765, report["level"], size=9, colour=(0.83, 0.86, 0.92))

    pdf_text(overview, 42, 690, "REPORT SCOPE", size=8, bold=True, colour=PDF_MUTED)
    pdf_text(overview, 42, 671, scope[:70], size=12, bold=True, colour=PDF_NAVY)
    pdf_text(overview, 360, 690, "GENERATED", size=8, bold=True, colour=PDF_MUTED)
    pdf_text(overview, 360, 671, generated_at[:19].replace("T", " "), size=10, colour=PDF_INK)

    metric_values = [
        ("Completion", f"{round(summary['completion_rate'] * 100)}%"),
        ("Submitted", f"{summary['submitted_count']} / {summary['expected_submissions']}"),
        ("Average score", average_score_label),
        ("Pupils", summary["student_count"]),
    ]
    for index, (label, value) in enumerate(metric_values):
        x = 42 + (index * 128)
        pdf_rect(overview, x, 588, 116, 62, fill=(1, 1, 1), stroke=PDF_BORDER)
        pdf_text(overview, x + 11, 630, label.upper(), size=7.5, bold=True, colour=PDF_MUTED)
        pdf_text(overview, x + 11, 604, value, size=18, bold=True, colour=PDF_NAVY)

    pdf_text(overview, 42, 548, "Rubric breakdown", size=17, bold=True, colour=PDF_NAVY)
    rubric_rows = [
        (
            "Content",
            rubric["content_average"],
            rubric["content_average_percentage"],
            rubric["content_max_score"],
            PDF_SAGE,
        ),
        (
            "Language",
            rubric["language_average"],
            rubric["language_average_percentage"],
            rubric["language_max_score"],
            PDF_PURPLE,
        ),
        (
            "Organisation",
            rubric["organisation_average"],
            rubric["organisation_average_percentage"],
            rubric["organisation_max_score"],
            PDF_AMBER,
        ),
    ]
    for index, (label, value, percentage, maximum, colour) in enumerate(rubric_rows):
        y = 514 - (index * 42)
        pdf_text(overview, 42, y + 10, label, size=10, bold=True, colour=PDF_INK)
        if value is not None and maximum is not None:
            score_label = f"{value} / {maximum}"
            score_ratio = float(value) / maximum
        elif percentage is not None:
            score_label = f"{percentage}%"
            score_ratio = float(percentage) / 100
        else:
            score_label = "-"
            score_ratio = 0
        pdf_text(overview, 490, y + 10, score_label, size=9, bold=True, colour=PDF_INK)
        pdf_rect(overview, 150, y + 8, 320, 9, fill=(0.93, 0.91, 0.87))
        width = max(0, min(320, score_ratio * 320))
        pdf_rect(overview, 150, y + 8, width, 9, fill=colour)

    pdf_text(overview, 42, 384, "Most useful teaching priorities", size=17, bold=True, colour=PDF_NAVY)
    pdf_text(
        overview,
        42,
        366,
        "Use the first pattern for a whole-class mini-lesson; use the others for focused groups.",
        size=9,
        colour=PDF_MUTED,
    )
    priority_rows = weaknesses[:3] or [{"weakness": "No recurring weakness yet", "count": 0}]
    for index, item in enumerate(priority_rows):
        y = 300 - (index * 66)
        fill = PDF_LAVENDER if index == 0 else (1, 1, 1)
        pdf_rect(overview, 42, y, 510, 52, fill=fill, stroke=PDF_BORDER)
        pdf_rect(overview, 54, y + 14, 23, 23, fill=PDF_CORAL if index == 0 else PDF_PURPLE)
        pdf_text(overview, 62, y + 21, index + 1, size=9, bold=True, colour=(1, 1, 1))
        pdf_text(overview, 90, y + 31, item["weakness"][:70], size=10, bold=True, colour=PDF_NAVY)
        if item["count"]:
            pupils = f"{item['count']} {'pupil' if item['count'] == 1 else 'pupils'}"
        else:
            pupils = "More reviewed writing needed"
        pdf_text(overview, 90, y + 15, pupils, size=8.5, colour=PDF_MUTED)

    pdf_line(overview, 42, 62, 552, 62)
    pdf_text(overview, 42, 42, "Teacher-owned evidence · AI suggestions require teacher review", size=8, colour=PDF_MUTED)
    pdf_text(overview, 520, 42, "1", size=8, colour=PDF_MUTED)

    pages = [overview]
    rows_per_page = 20
    for page_index, start in enumerate(range(0, len(rows), rows_per_page), start=2):
        commands: list[str] = []
        pdf_rect(commands, 0, 0, 595, 842, fill=PDF_IVORY)
        pdf_rect(commands, 0, 772, 595, 70, fill=PDF_NAVY)
        pdf_text(commands, 42, 810, "Student writing overview", size=20, bold=True, colour=(1, 1, 1))
        pdf_text(commands, 42, 788, f"{report['class_name']} · {scope[:62]}", size=9, colour=(0.83, 0.86, 0.92))

        columns = [(42, "PUPIL"), (170, "WRITING TASK"), (362, "WORDS"), (415, "SCORE"), (474, "STATUS")]
        pdf_rect(commands, 42, 727, 510, 28, fill=PDF_LAVENDER)
        for x, label in columns:
            pdf_text(commands, x + 5, 738, label, size=7.5, bold=True, colour=PDF_NAVY)

        for row_index, row in enumerate(rows[start : start + rows_per_page]):
            y = 699 - (row_index * 31)
            if row_index % 2 == 1:
                pdf_rect(commands, 42, y - 8, 510, 31, fill=(0.985, 0.98, 0.96))
            pdf_text(commands, 47, y + 6, row["student_name"][:22], size=8.5, bold=True, colour=PDF_NAVY)
            pdf_text(commands, 47, y - 5, row["student_number"][:18], size=6.8, colour=PDF_MUTED)
            pdf_text(commands, 175, y + 2, row["task_title"][:34], size=7.8, colour=PDF_INK)
            pdf_text(commands, 367, y + 2, row["word_count"] or "-", size=8, colour=PDF_INK)
            score = (
                f"{row['total_score']} / {row['total_max_score']}"
                if row["total_score"] is not None
                else "-"
            )
            pdf_text(commands, 420, y + 2, score, size=8, bold=True, colour=PDF_INK)
            status = "Missing"
            status_colour = PDF_MUTED
            if row["submitted"]:
                status = "Returned" if row["review_status"] == "RELEASED" else "In review"
                status_colour = PDF_SAGE if status == "Returned" else PDF_AMBER
            pdf_text(commands, 479, y + 2, status, size=7.5, bold=True, colour=status_colour)
            pdf_line(commands, 42, y - 9, 552, y - 9, (0.91, 0.89, 0.86))

        pdf_line(commands, 42, 62, 552, 62)
        pdf_text(commands, 42, 42, "Confidential school report · Generated by English AI Writing Platform", size=8, colour=PDF_MUTED)
        pdf_text(commands, 520, 42, page_index, size=8, colour=PDF_MUTED)
        pages.append(commands)

    return build_pdf_document(pages)


async def audit_export(
    db: AsyncSession, request: Request, user: User, class_id: str, task_id: str | None, fmt: str
) -> None:
    await write_audit_log(
        db,
        request,
        "CLASS_REPORT_EXPORTED",
        user,
        {"class_id": class_id, "task_id": task_id, "format": fmt},
    )
    await db.commit()


@router.get("/teacher/reports/classes/{class_id}/exports")
async def list_teacher_class_report_exports(
    class_id: str,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    await require_teacher_class(db, user, class_id)
    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.school_id == user.school_id,
            AuditLog.action == "CLASS_REPORT_EXPORTED",
        )
        .order_by(desc(AuditLog.created_at))
        .limit(100)
    )
    exports = []
    for row in result.scalars().all():
        metadata = row.event_metadata or {}
        if metadata.get("class_id") != class_id:
            continue
        exports.append(
            {
                "id": row.id,
                "action": row.action,
                "class_id": metadata.get("class_id"),
                "task_id": metadata.get("task_id"),
                "format": metadata.get("format"),
                "actor_user_id": row.actor_user_id,
                "actor_role": row.actor_role,
                "created_at": row.created_at.isoformat(),
            }
        )
    return success_response(request, {"exports": exports})


@router.get("/teacher/reports/classes/{class_id}/export.csv")
async def export_teacher_class_report_csv(
    class_id: str,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
    task_id: Annotated[str | None, Query()] = None,
) -> Response:
    try:
        payload = await build_class_report_payload(db, user, class_id, task_id)
        csv_body = class_report_to_csv(payload)
        await audit_export(db, request, user, class_id, task_id, "csv")
    except ApiException:
        raise
    except Exception as exc:
        raise ApiException(ErrorCode.EXPORT_FAILED, "CSV export failed.", 500) from exc
    return Response(
        csv_body,
        media_type="text/csv; charset=utf-8",
        headers={"content-disposition": f'attachment; filename="class-report-{class_id}.csv"'},
    )


@router.get("/teacher/reports/classes/{class_id}/export.pdf")
async def export_teacher_class_report_pdf(
    class_id: str,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
    task_id: Annotated[str | None, Query()] = None,
) -> Response:
    try:
        payload = await build_class_report_payload(db, user, class_id, task_id)
        pdf_body = build_class_report_pdf(payload, utc_now().isoformat())
        await audit_export(db, request, user, class_id, task_id, "pdf")
    except ApiException:
        raise
    except Exception as exc:
        raise ApiException(ErrorCode.EXPORT_FAILED, "PDF export failed.", 500) from exc
    return Response(
        pdf_body,
        media_type="application/pdf",
        headers={"content-disposition": f'attachment; filename="class-report-{class_id}.pdf"'},
    )
