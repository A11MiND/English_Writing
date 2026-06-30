from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_DNS, uuid5


SCHOOL_ID = "11111111-1111-4111-8111-111111111111"
DEFAULT_PASSWORD = "Password123!"
DEFAULT_BASE_URL = "https://api.minimaxi.com/v1"
DEFAULT_MODEL = "MiniMax-M3"


@dataclass(frozen=True)
class StudentRow:
    email: str
    display_name: str
    student_number: str
    level: str
    class_name: str
    sub: str


def password_hash(password: str, salt_text: str, iterations: int = 210_000) -> str:
    salt = salt_text.encode("utf-8")
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived.hex()}"


def stable_sub(email: str) -> str:
    return str(uuid5(NAMESPACE_DNS, f"english-ai-writing-platform:{email.lower()}"))


def student_rows(count: int) -> list[StudentRow]:
    classes = [("P4", "P4A"), ("P5", "P5A"), ("P6", "P6A")]
    rows: list[StudentRow] = []
    for index in range(1, count + 1):
        level, class_name = classes[(index - 1) % len(classes)]
        email = f"uat.student.{index:03d}@wfjosephlee.edu.hk"
        rows.append(
            StudentRow(
                email=email,
                display_name=f"UAT Student {index:03d}",
                student_number=f"UAT{index:03d}",
                level=level,
                class_name=class_name,
                sub=stable_sub(email),
            )
        )
    return rows


def teacher_rows() -> list[dict[str, str]]:
    return [
        {
            "external_user_id": stable_sub("uat.teacher.001@wfjosephlee.edu.hk"),
            "email": "uat.teacher.001@wfjosephlee.edu.hk",
            "display_name": "UAT English Teacher 001",
            "staff_code": "T-UAT-001",
        },
        {
            "external_user_id": stable_sub("uat.teacher.002@wfjosephlee.edu.hk"),
            "email": "uat.teacher.002@wfjosephlee.edu.hk",
            "display_name": "UAT English Teacher 002",
            "staff_code": "T-UAT-002",
        },
    ]


def openauth_users(students: list[StudentRow]) -> list[dict[str, str | None]]:
    users: list[dict[str, str | None]] = []
    for teacher in teacher_rows():
        users.append(
            {
                "email": teacher["email"],
                "password_hash": password_hash(DEFAULT_PASSWORD, f"{teacher['email']}-local-dev-salt"),
                "sub": teacher["external_user_id"],
                "school_id": SCHOOL_ID,
                "role": "TEACHER",
                "status": "ACTIVE",
            }
        )
    for student in students:
        users.append(
            {
                "email": student.email,
                "password_hash": password_hash(DEFAULT_PASSWORD, f"{student.email}-local-dev-salt"),
                "sub": student.sub,
                "school_id": SCHOOL_ID,
                "role": "STUDENT",
                "status": "ACTIVE",
            }
        )
    return users


def call_minimax(
    *,
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    timeout_seconds: int,
) -> dict:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You generate fictional primary-school English writing UAT fixtures. "
                    "Return one strict JSON object only. The first character must be { and the last "
                    "character must be }. Do not include markdown. Do not include real people or personal data."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 12000,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"MiniMax returned HTTP {exc.code}: {exc.read()[:300]!r}") from exc
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("MiniMax response did not include choices.")
    content = choices[0].get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("MiniMax response did not include message content.")
    return parse_json_content(content)


def parse_json_content(content: str) -> dict:
    text = content.strip()
    if "</think>" in text:
        text = text.split("</think>", 1)[1].strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            extracted = text[start : end + 1]
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                repaired = repair_loose_json(extracted)
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError as exc:
                    Path("/private/tmp/minimax-last-response.txt").write_text(text, encoding="utf-8")
                    Path("/private/tmp/minimax-last-repaired.json").write_text(repaired, encoding="utf-8")
                    raise RuntimeError(
                        "MiniMax response was not parseable after loose repair. "
                        "Saved /private/tmp/minimax-last-response.txt and "
                        "/private/tmp/minimax-last-repaired.json for local inspection."
                    ) from exc
        preview = text[:300].replace("\n", "\\n")
        raise RuntimeError(f"MiniMax response was not parseable JSON. Preview: {preview!r}") from None
        raise


def repair_loose_json(text: str) -> str:
    repaired = text.strip()
    repaired = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', repaired)
    repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)
    repaired = repaired.replace("'", '"')
    return repaired


def minimax_fixture_prompt(topic_count: int, essay_count: int) -> str:
    return f"""
Create fictional UAT fixture data for W F Joseph Lee Primary School English AI Writing Platform.

Return JSON with exactly these top-level keys:
- writing_topics: array of {{topic_title, level, mode, genre, instruction, word_minimum, word_maximum, exam_duration_minutes}}
- sample_essays: array of {{topic_title, level, mode, approximate_score_band, essay_text, expected_weaknesses}}

Rules:
- Generate exactly {topic_count} total writing_topics across P4, P5 and P6.
- Distribute topics across all three levels as evenly as possible.
- Include both PRACTICE and EXAM modes.
- EXAM topics must set exam_duration_minutes to 30, 45 or 60.
- PRACTICE topics must set exam_duration_minutes to null.
- Generate {essay_count} sample_essays.
- Use Hong Kong primary-school appropriate contexts.
- Keep all names fictional and generic.
- Essays should include realistic grammar, content and organisation issues.
- Return only valid JSON.
- First output character must be {{ and final output character must be }}.
""".strip()


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MiniMax-backed UAT fixture data.")
    parser.add_argument("--student-count", type=int, default=470)
    parser.add_argument("--topic-count", type=int, default=11)
    parser.add_argument("--essay-count", type=int, default=30)
    parser.add_argument("--out-dir", default="tests/fixtures/uat/minimax")
    parser.add_argument("--base-url", default=os.getenv("MINIMAX_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--model", default=os.getenv("MINIMAX_MODEL", DEFAULT_MODEL))
    parser.add_argument("--timeout-seconds", type=int, default=60)
    args = parser.parse_args()

    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        raise SystemExit("Set MINIMAX_API_KEY in your local environment. The key is never written to output files.")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    students = student_rows(args.student_count)
    generated = call_minimax(
        api_key=api_key,
        base_url=args.base_url,
        model=args.model,
        timeout_seconds=args.timeout_seconds,
        prompt=minimax_fixture_prompt(args.topic_count, args.essay_count),
    )

    write_csv(
        out_dir / "students.csv",
        [
            {
                "external_user_id": row.sub,
                "email": row.email,
                "display_name": row.display_name,
                "student_number": row.student_number,
                "level": row.level,
                "class_name": row.class_name,
            }
            for row in students
        ],
        ["external_user_id", "email", "display_name", "student_number", "level", "class_name"],
    )
    write_csv(
        out_dir / "teachers.csv",
        teacher_rows(),
        ["external_user_id", "email", "display_name", "staff_code"],
    )
    (out_dir / "openauth-users.json").write_text(
        json.dumps(openauth_users(students), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out_dir / "writing-fixtures.json").write_text(
        json.dumps(
            {
                "generated_at_epoch": int(time.time()),
                "provider": "minimax",
                "model": args.model,
                "student_count": args.student_count,
                **generated,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"out_dir": str(out_dir), "student_count": len(students), "model": args.model}, sort_keys=True))


if __name__ == "__main__":
    main()
