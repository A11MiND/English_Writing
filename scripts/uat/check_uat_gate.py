from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_EVIDENCE_DIR = Path("docs/uat-evidence/2026-06-29")
REQUIRED_STRESS_SCENARIOS = {
    "150_students_login_within_10_minutes",
    "100_concurrent_students_writing_autosave_and_suggestions",
    "470_submissions_within_30_minutes",
    "470_essays_queued_for_marking",
    "teacher_generates_report_after_marking_queue",
}
RUNTIME_SOURCE_DIRS = [
    Path("apps/api/app"),
    Path("apps/auth"),
    Path("workers/marking-worker"),
    Path("services/grammar-service"),
]
RUNTIME_FORBIDDEN_SNIPPETS = [
    "PROVIDER_PRESETS = {\"mock\"",
    "LLM_PROVIDER=mock",
    "fake_marking",
    "fake suggestion",
    "return_mock",
]


@dataclass
class Check:
    name: str
    passed: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{path}:{line_number} is not valid JSONL: {exc}") from exc
    return rows


def latest_stress_file(evidence_dir: Path) -> Path | None:
    files = sorted(evidence_dir.glob("stress-*.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True)
    return files[0] if files else None


def check_required_files(evidence_dir: Path) -> list[Check]:
    required = [
        Path("docs/uat-readiness.md"),
        Path("scripts/uat/generate_minimax_uat_data.py"),
        Path("scripts/uat/apply_uat_fixtures.py"),
        Path("tests/unit/test_uat_fixture_scripts.py"),
    ]
    checks = [
        Check(f"required_file:{path}", path.exists(), "exists" if path.exists() else "missing")
        for path in required
    ]
    checks.append(
        Check(
            "evidence_dir",
            evidence_dir.exists(),
            str(evidence_dir) if evidence_dir.exists() else f"{evidence_dir} missing",
        )
    )
    return checks


def check_runtime_no_obvious_mocks() -> Check:
    hits: list[str] = []
    for source_dir in RUNTIME_SOURCE_DIRS:
        if not source_dir.exists():
            continue
        for path in source_dir.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for snippet in RUNTIME_FORBIDDEN_SNIPPETS:
                if snippet in text:
                    hits.append(f"{path}:{snippet}")
    return Check(
        "runtime_no_obvious_mock_paths",
        not hits,
        "no banned runtime snippets" if not hits else "; ".join(hits[:10]),
    )


def check_stress_evidence(evidence_dir: Path, require_distinct_students: bool) -> list[Check]:
    path = latest_stress_file(evidence_dir)
    if path is None:
        return [Check("stress_evidence", False, f"No stress-*.jsonl found under {evidence_dir}.")]

    rows = load_jsonl(path)
    rows_by_scenario = {row.get("scenario"): row for row in rows}
    checks: list[Check] = [
        Check("stress_evidence_file", True, str(path)),
    ]
    for scenario in sorted(REQUIRED_STRESS_SCENARIOS):
        row = rows_by_scenario.get(scenario)
        checks.append(
            Check(
                f"stress_scenario:{scenario}",
                bool(row and row.get("passed") is True),
                "passed" if row and row.get("passed") is True else "missing or failed",
            )
        )

    if require_distinct_students:
        summary = rows_by_scenario.get("stress_summary") or {}
        distinct_count = int(summary.get("distinct_student_credentials") or 0)
        distinct_rows = [
            row
            for row in rows
            if isinstance(row.get("credential_strategy"), str)
            and row["credential_strategy"].startswith("distinct_student")
        ]
        checks.append(
            Check(
                "stress_distinct_student_credentials",
                distinct_count >= 470 and len(distinct_rows) >= 3,
                f"distinct_student_credentials={distinct_count}, distinct_scenarios={len(distinct_rows)}",
            )
        )
    return checks


def check_exports(evidence_dir: Path) -> list[Check]:
    csv_files = list(evidence_dir.glob("class-report-*.csv"))
    pdf_files = list(evidence_dir.glob("class-report-*.pdf"))
    return [
        Check("report_csv_evidence", bool(csv_files), f"{len(csv_files)} csv file(s)"),
        Check("report_pdf_evidence", bool(pdf_files), f"{len(pdf_files)} pdf file(s)"),
    ]


def check_optional_fixture_apply(fixture_dir: Path, required: bool) -> Check:
    path = fixture_dir / "writing-fixtures.applied.json"
    if not required:
        return Check("writing_fixture_apply_evidence", True, "not required for this gate run")
    if not path.exists():
        return Check("writing_fixture_apply_evidence", False, f"{path} missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    created = len(payload.get("created_tasks") or [])
    reused = len(payload.get("reused_tasks") or [])
    return Check(
        "writing_fixture_apply_evidence",
        created + reused > 0,
        f"created_tasks={created}, reused_tasks={reused}",
    )


def run_gate(
    *,
    evidence_dir: Path,
    fixture_dir: Path,
    require_distinct_students: bool,
    require_writing_fixtures_applied: bool,
) -> list[Check]:
    checks: list[Check] = []
    checks.extend(check_required_files(evidence_dir))
    checks.append(check_runtime_no_obvious_mocks())
    checks.extend(check_stress_evidence(evidence_dir, require_distinct_students))
    checks.extend(check_exports(evidence_dir))
    checks.append(check_optional_fixture_apply(fixture_dir, require_writing_fixtures_applied))
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Check UAT readiness evidence without silently passing gaps.")
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    parser.add_argument("--fixture-dir", default="tests/fixtures/uat/minimax")
    parser.add_argument("--require-distinct-student-stress", action="store_true")
    parser.add_argument("--require-writing-fixtures-applied", action="store_true")
    args = parser.parse_args()

    checks = run_gate(
        evidence_dir=Path(args.evidence_dir),
        fixture_dir=Path(args.fixture_dir),
        require_distinct_students=args.require_distinct_student_stress,
        require_writing_fixtures_applied=args.require_writing_fixtures_applied,
    )
    payload = {
        "passed": all(check.passed for check in checks),
        "checks": [check.as_dict() for check in checks],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not payload["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
