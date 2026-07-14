from typing import Annotated, Literal
from uuid import UUID
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AccountStatus, Role, require_roles, write_audit_log
from app.core.database import get_session
from app.core.responses import ApiException, ErrorCode, success_response
from app.models import Class, ClassMembership, StudentProfile, TeacherProfile, User
from app.services.identity_provisioning import provision_identity

router = APIRouter(prefix="/api", tags=["school-data"])

SUPPORTED_LEVELS = {"P4", "P5", "P6"}


class CreateClassRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    level: str = Field(min_length=2, max_length=16)
    academic_year: str = Field(default="2026-2027", min_length=4, max_length=16)

    @field_validator("name", "level", "academic_year")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in SUPPORTED_LEVELS:
            raise ValueError("Level must be P4, P5 or P6.")
        return normalized


class ImportUserRow(BaseModel):
    external_user_id: str | None = Field(default=None, min_length=36, max_length=36)
    email: str = Field(min_length=3, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    student_number: str | None = Field(default=None, max_length=64)
    level: str | None = Field(default=None, max_length=16)
    class_name: str | None = Field(default=None, max_length=64)
    staff_code: str | None = Field(default=None, max_length=64)

    @field_validator("external_user_id")
    @classmethod
    def validate_external_user_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        try:
            UUID(cleaned)
        except ValueError as exc:
            raise ValueError("external_user_id must be a UUID.") from exc
        return cleaned

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Valid email is required.")
        return normalized

    @field_validator("display_name", "student_number", "level", "class_name", "staff_code")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ImportUsersRequest(BaseModel):
    role: Literal["TEACHER", "STUDENT"]
    rows: list[ImportUserRow] = Field(min_length=1, max_length=500)


class CreateTeacherStudentRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=3, max_length=255)
    temporary_password: str = Field(min_length=8, max_length=128)
    class_id: str = Field(min_length=36, max_length=36)
    student_number: str | None = Field(default=None, min_length=2, max_length=64)

    @field_validator("display_name", "student_number")
    @classmethod
    def clean_teacher_student_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("email")
    @classmethod
    def clean_teacher_student_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Valid email is required.")
        return normalized


async def school_scope(db: AsyncSession, user: User) -> str:
    if user.school_id:
        return user.school_id
    result = await db.execute(select(User.school_id).where(User.school_id.is_not(None)).limit(1))
    school_id = result.scalar_one_or_none()
    if not school_id:
        raise ApiException(ErrorCode.ACCESS_DENIED, "No school scope is available.", 403)
    return school_id


def serialize_class(row: Class, teacher_count: int = 0, student_count: int = 0) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "level": row.level,
        "academic_year": row.academic_year,
        "status": row.status,
        "teacher_count": teacher_count,
        "student_count": student_count,
    }


@router.get("/admin/classes")
async def list_admin_classes(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.SYSTEM_ADMIN, Role.SCHOOL_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    school_id = await school_scope(db, user)
    result = await db.execute(
        select(
            Class,
            func.count(ClassMembership.id)
            .filter(ClassMembership.membership_role == Role.TEACHER)
            .label("teacher_count"),
            func.count(ClassMembership.id)
            .filter(ClassMembership.membership_role == Role.STUDENT)
            .label("student_count"),
        )
        .outerjoin(
            ClassMembership,
            (ClassMembership.class_id == Class.id) & (ClassMembership.school_id == school_id),
        )
        .where(Class.school_id == school_id)
        .group_by(Class.id)
        .order_by(Class.level, Class.name)
    )
    classes = [serialize_class(row, teacher_count, student_count) for row, teacher_count, student_count in result]
    return success_response(request, {"classes": classes})


@router.post("/admin/classes")
async def create_admin_class(
    payload: CreateClassRequest,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.SYSTEM_ADMIN, Role.SCHOOL_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    school_id = await school_scope(db, user)
    existing = await db.execute(
        select(Class).where(
            Class.school_id == school_id,
            Class.name == payload.name,
            Class.academic_year == payload.academic_year,
        )
    )
    if existing.scalar_one_or_none():
        raise ApiException(ErrorCode.DUPLICATE_RECORD, "Class already exists.", 409)

    row = Class(
        school_id=school_id,
        name=payload.name,
        level=payload.level,
        academic_year=payload.academic_year,
        status="ACTIVE",
    )
    db.add(row)
    await write_audit_log(
        db,
        request,
        "CLASS_CREATED",
        user,
        {"class_name": payload.name, "academic_year": payload.academic_year},
    )
    await db.commit()
    await db.refresh(row)
    return success_response(request, {"class": serialize_class(row)})


@router.get("/admin/users")
async def list_admin_users(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.SYSTEM_ADMIN, Role.SCHOOL_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    school_id = await school_scope(db, user)
    result = await db.execute(
        select(User, TeacherProfile, StudentProfile, Class)
        .outerjoin(TeacherProfile, TeacherProfile.user_id == User.id)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .outerjoin(Class, Class.id == StudentProfile.current_class_id)
        .where(User.school_id == school_id)
        .order_by(User.role, User.display_name)
    )
    users = []
    for account, teacher_profile, student_profile, class_row in result:
        users.append(
            {
                "id": account.id,
                "email": account.email,
                "display_name": account.display_name,
                "role": account.role,
                "status": account.status,
                "staff_code": teacher_profile.staff_code if teacher_profile else None,
                "student_number": student_profile.student_number if student_profile else None,
                "level": student_profile.level if student_profile else None,
                "class_name": class_row.name if class_row else None,
            }
        )
    return success_response(request, {"users": users})


@router.post("/admin/import/users")
async def import_admin_users(
    payload: ImportUsersRequest,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.SYSTEM_ADMIN, Role.SCHOOL_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    school_id = await school_scope(db, user)
    successful: list[dict] = []
    rejected: list[dict] = []
    seen_emails: set[str] = set()

    existing_email_result = await db.execute(select(User.email).where(User.school_id == school_id))
    existing_emails = set(existing_email_result.scalars().all())
    existing_id_result = await db.execute(select(User.id))
    existing_ids = set(existing_id_result.scalars().all())
    existing_student_numbers_result = await db.execute(
        select(StudentProfile.student_number).where(StudentProfile.school_id == school_id)
    )
    existing_student_numbers = set(existing_student_numbers_result.scalars().all())
    classes_result = await db.execute(select(Class).where(Class.school_id == school_id))
    classes_by_name = {row.name.upper(): row for row in classes_result.scalars().all()}

    for index, row in enumerate(payload.rows, start=1):
        reasons: list[str] = []
        email = row.email.lower()
        if email in existing_emails or email in seen_emails:
            reasons.append("Duplicate email.")
        seen_emails.add(email)
        if row.external_user_id and row.external_user_id in existing_ids:
            reasons.append("Duplicate external user id.")

        class_row = None
        if payload.role == Role.STUDENT:
            if not row.student_number:
                reasons.append("Student number is required.")
            elif row.student_number in existing_student_numbers:
                reasons.append("Duplicate student number.")
            if not row.level or row.level.upper() not in SUPPORTED_LEVELS:
                reasons.append("Level must be P4, P5 or P6.")
            if not row.class_name:
                reasons.append("Class name is required.")
            else:
                class_row = classes_by_name.get(row.class_name.upper())
                if class_row is None:
                    reasons.append("Class not found.")
        elif row.class_name:
            class_row = classes_by_name.get(row.class_name.upper())
            if class_row is None:
                reasons.append("Class not found.")

        if reasons:
            rejected.append({"row": index, "email": row.email, "reasons": reasons})
            continue

        account_kwargs = {}
        if row.external_user_id:
            account_kwargs["id"] = row.external_user_id
        account = User(
            **account_kwargs,
            school_id=school_id,
            email=email,
            display_name=row.display_name,
            role=payload.role,
            status=AccountStatus.ACTIVE,
        )
        db.add(account)
        await db.flush()

        if payload.role == Role.TEACHER:
            db.add(
                TeacherProfile(
                    school_id=school_id,
                    user_id=account.id,
                    staff_code=row.staff_code,
                )
            )
            if class_row:
                db.add(
                    ClassMembership(
                        school_id=school_id,
                        class_id=class_row.id,
                        user_id=account.id,
                        membership_role=Role.TEACHER,
                    )
                )
        else:
            db.add(
                StudentProfile(
                    school_id=school_id,
                    user_id=account.id,
                    student_number=row.student_number or "",
                    level=(row.level or "").upper(),
                    current_class_id=class_row.id if class_row else None,
                )
            )
            if class_row:
                db.add(
                    ClassMembership(
                        school_id=school_id,
                        class_id=class_row.id,
                        user_id=account.id,
                        membership_role=Role.STUDENT,
                    )
                )
            if row.student_number:
                existing_student_numbers.add(row.student_number)

        successful.append({"row": index, "email": email, "role": payload.role})
        if row.external_user_id:
            existing_ids.add(row.external_user_id)

    try:
        await write_audit_log(
            db,
            request,
            "USERS_IMPORTED",
            user,
            {
                "role": payload.role,
                "successful_count": len(successful),
                "rejected_count": len(rejected),
            },
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ApiException(ErrorCode.DUPLICATE_RECORD, "Import contains duplicate records.", 409) from exc

    return success_response(
        request,
        {
            "successful_rows": successful,
            "rejected_rows": rejected,
            "successful_count": len(successful),
            "rejected_count": len(rejected),
        },
    )


@router.get("/teacher/classes")
async def list_teacher_classes(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    result = await db.execute(
        select(Class)
        .join(ClassMembership, ClassMembership.class_id == Class.id)
        .where(
            Class.school_id == user.school_id,
            ClassMembership.school_id == user.school_id,
            ClassMembership.user_id == user.id,
            ClassMembership.membership_role == Role.TEACHER,
        )
        .order_by(Class.level, Class.name)
    )
    classes = [serialize_class(row) for row in result.scalars().all()]
    return success_response(request, {"classes": classes})


@router.get("/teacher/students")
async def list_teacher_students(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    teacher_classes = (
        select(ClassMembership.class_id)
        .where(
            ClassMembership.school_id == user.school_id,
            ClassMembership.user_id == user.id,
            ClassMembership.membership_role == Role.TEACHER,
        )
    )
    result = await db.execute(
        select(User, StudentProfile, Class)
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .join(Class, Class.id == StudentProfile.current_class_id)
        .where(
            User.school_id == user.school_id,
            User.role == Role.STUDENT,
            StudentProfile.current_class_id.in_(teacher_classes),
        )
        .order_by(Class.name, User.display_name)
    )
    students = [
        {
            "id": student.id,
            "display_name": student.display_name,
            "email": student.email,
            "status": student.status,
            "student_number": profile.student_number,
            "level": profile.level,
            "class_id": class_row.id,
            "class_name": class_row.name,
        }
        for student, profile, class_row in result
    ]
    return success_response(request, {"students": students})


@router.post("/teacher/students")
async def create_teacher_student(
    payload: CreateTeacherStudentRequest,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    class_result = await db.execute(
        select(Class)
        .join(ClassMembership, ClassMembership.class_id == Class.id)
        .where(
            Class.id == payload.class_id,
            Class.school_id == user.school_id,
            ClassMembership.school_id == user.school_id,
            ClassMembership.user_id == user.id,
            ClassMembership.membership_role == Role.TEACHER,
        )
    )
    class_row = class_result.scalar_one_or_none()
    if class_row is None:
        raise ApiException(ErrorCode.ACCESS_DENIED, "Teacher is not assigned to this class.", 403)
    existing_email = await db.execute(select(User.id).where(User.email == payload.email))
    if existing_email.scalar_one_or_none() is not None:
        raise ApiException(ErrorCode.DUPLICATE_RECORD, "Email is already registered.", 409)
    if payload.student_number:
        existing_number = await db.execute(
            select(StudentProfile.id).where(
                StudentProfile.school_id == user.school_id,
                StudentProfile.student_number == payload.student_number,
            )
        )
        if existing_number.scalar_one_or_none() is not None:
            raise ApiException(ErrorCode.DUPLICATE_RECORD, "Student number is already registered.", 409)

    user_id = str(uuid4())
    student_number = payload.student_number or f"P{user_id[:6].upper()}"
    await provision_identity(
        email=payload.email,
        password=payload.temporary_password,
        user_id=user_id,
        school_id=user.school_id,
        role=Role.STUDENT,
    )
    student = User(
        id=user_id,
        school_id=user.school_id,
        email=payload.email,
        display_name=payload.display_name,
        role=Role.STUDENT,
        status=AccountStatus.ACTIVE,
    )
    db.add(student)
    await db.flush()
    db.add(
        StudentProfile(
            school_id=user.school_id,
            user_id=student.id,
            student_number=student_number,
            level=class_row.level,
            current_class_id=class_row.id,
        )
    )
    db.add(
        ClassMembership(
            school_id=user.school_id,
            class_id=class_row.id,
            user_id=student.id,
            membership_role=Role.STUDENT,
        )
    )
    await write_audit_log(
        db,
        request,
        "STUDENT_CREATED_BY_TEACHER",
        user,
        {"student_id": student.id, "class_id": class_row.id},
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ApiException(ErrorCode.DUPLICATE_RECORD, "Student account already exists.", 409) from exc
    return success_response(
        request,
        {
            "student": {
                "id": student.id,
                "display_name": student.display_name,
                "email": student.email,
                "status": student.status,
                "student_number": student_number,
                "level": class_row.level,
                "class_id": class_row.id,
                "class_name": class_row.name,
            }
        },
    )


@router.get("/student/profile")
async def get_student_profile(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    result = await db.execute(
        select(StudentProfile, Class)
        .outerjoin(Class, Class.id == StudentProfile.current_class_id)
        .where(StudentProfile.school_id == user.school_id, StudentProfile.user_id == user.id)
    )
    row = result.one_or_none()
    if row is None:
        raise ApiException(ErrorCode.NOT_FOUND, "Student profile not found.", status.HTTP_404_NOT_FOUND)
    profile, class_row = row
    return success_response(
        request,
        {
            "profile": {
                "student_number": profile.student_number,
                "level": profile.level,
                "class_name": class_row.name if class_row else None,
            }
        },
    )
