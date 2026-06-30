from __future__ import annotations

import csv
from collections import Counter
from io import StringIO
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

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
    School,
    StudentProfile,
    Submission,
    TeacherReview,
    User,
    WritingTask,
    utc_now,
)

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


def score_bucket(score: int | None) -> str:
    if score is None:
        return "unscored"
    if score <= 5:
        return "0-5"
    if score <= 10:
        return "6-10"
    if score <= 15:
        return "11-15"
    return "16+"


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

    completion_rows: list[dict] = []
    score_values: list[int] = []
    content_scores: list[int] = []
    language_scores: list[int] = []
    organisation_scores: list[int] = []
    distribution = Counter({"0-5": 0, "6-10": 0, "11-15": 0, "16+": 0, "unscored": 0})
    weakness_counts: Counter[str] = Counter()

    for student, profile in students:
        for task in tasks:
            submission = submissions_by_key.get((student.id, task.id))
            marking = marking_by_submission.get(submission.id) if submission else None
            review = review_by_submission.get(submission.id) if submission else None
            content, language, organisation, total = score_from_review_or_ai(review, marking)
            distribution[score_bucket(total)] += 1
            if total is not None:
                score_values.append(total)
            if content is not None:
                content_scores.append(content)
            if language is not None:
                language_scores.append(language)
            if organisation is not None:
                organisation_scores.append(organisation)
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
                    "review_status": review.status if review else None,
                    "marking_status": marking.status if marking else None,
                }
            )

    expected_submissions = len(students) * len(tasks)
    submitted_count = sum(1 for row in completion_rows if row["submitted"])
    average_total = round(sum(score_values) / len(score_values), 2) if score_values else None
    rubric_breakdown = {
        "content_average": round(sum(content_scores) / len(content_scores), 2)
        if content_scores
        else None,
        "language_average": round(sum(language_scores) / len(language_scores), 2)
        if language_scores
        else None,
        "organisation_average": round(sum(organisation_scores) / len(organisation_scores), 2)
        if organisation_scores
        else None,
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
            "language_score",
            "organisation_score",
            "total_score",
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


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_simple_pdf(lines: list[str]) -> bytes:
    content_lines = ["BT", "/F1 10 Tf", "50 800 Td", "14 TL"]
    for line in lines[:48]:
        content_lines.append(f"({pdf_escape(line[:110])}) Tj")
        content_lines.append("T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("utf-8")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return bytes(pdf)


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
        summary = payload["summary"]
        rubric = payload["rubric_breakdown"]
        report = payload["class_report"]
        lines = [
            "English AI Writing Platform - Class Report",
            f"School: {report['school_name']}",
            f"Class: {report['class_name']} ({report['level']})",
            f"Task scope: {report['task_id'] or 'All assigned tasks'}",
            f"Generated at: {utc_now().isoformat()}",
            f"Students: {summary['student_count']}",
            f"Assigned tasks: {summary['assigned_task_count']}",
            f"Submitted: {summary['submitted_count']} / {summary['expected_submissions']}",
            f"Average total score: {summary['average_total_score']}",
            "",
            "Rubric breakdown:",
            f"- Content average: {rubric['content_average']}",
            f"- Language average: {rubric['language_average']}",
            f"- Organisation average: {rubric['organisation_average']}",
            "",
            "Common weaknesses:",
        ]
        lines.extend(
            f"- {item['weakness']}: {item['count']}" for item in payload["common_weaknesses"]
        )
        lines.append("")
        lines.append("Completion:")
        lines.extend(
            f"{row['student_number']} {row['student_name']} - {row['task_title']}: "
            f"{'submitted' if row['submitted'] else 'missing'} total={row['total_score']}"
            for row in payload["completion_rows"][:30]
        )
        pdf_body = build_simple_pdf(lines)
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
