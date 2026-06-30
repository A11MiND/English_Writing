import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "uat" / "check_uat_gate.py"


spec = importlib.util.spec_from_file_location("check_uat_gate", SCRIPT_PATH)
check_uat_gate = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules["check_uat_gate"] = check_uat_gate
spec.loader.exec_module(check_uat_gate)


def write_stress(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def passing_stress_rows(distinct_count: int = 0) -> list[dict]:
    rows = [
        {"scenario": scenario, "passed": True}
        for scenario in sorted(check_uat_gate.REQUIRED_STRESS_SCENARIOS)
    ]
    if distinct_count:
        for row in rows:
            if row["scenario"] in {
                "150_students_login_within_10_minutes",
                "100_concurrent_students_writing_autosave_and_suggestions",
                "470_submissions_within_30_minutes",
            }:
                row["credential_strategy"] = "distinct_student_accounts"
        rows.append({"scenario": "stress_summary", "distinct_student_credentials": distinct_count})
    return rows


def test_check_stress_evidence_passes_required_scenarios(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    write_stress(evidence_dir / "stress-20260629T010000Z.jsonl", passing_stress_rows())

    checks = check_uat_gate.check_stress_evidence(evidence_dir, require_distinct_students=False)

    assert all(check.passed for check in checks)


def test_check_stress_evidence_can_require_distinct_students(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    write_stress(evidence_dir / "stress-20260629T010000Z.jsonl", passing_stress_rows())

    checks = check_uat_gate.check_stress_evidence(evidence_dir, require_distinct_students=True)

    distinct_check = next(check for check in checks if check.name == "stress_distinct_student_credentials")
    assert distinct_check.passed is False


def test_check_optional_fixture_apply_requires_real_task_output(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    (fixture_dir / "writing-fixtures.applied.json").write_text(
        json.dumps({"created_tasks": [{"id": "task-1"}], "reused_tasks": []}),
        encoding="utf-8",
    )

    check = check_uat_gate.check_optional_fixture_apply(fixture_dir, required=True)

    assert check.passed is True
    assert "created_tasks=1" in check.detail
