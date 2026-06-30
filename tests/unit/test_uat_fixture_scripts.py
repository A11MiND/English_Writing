import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "uat" / "apply_uat_fixtures.py"


spec = importlib.util.spec_from_file_location("apply_uat_fixtures", SCRIPT_PATH)
apply_uat_fixtures = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(apply_uat_fixtures)


def envelope(data: dict) -> bytes:
    return json.dumps({"success": True, "data": data, "request_id": "test"}).encode("utf-8")


class FakeApiSession:
    def __init__(self) -> None:
        self.classes = [{"id": "class-p5a", "name": "P5A", "level": "P5"}]
        self.rubrics: list[dict[str, Any]] = []
        self.tasks: list[dict[str, Any]] = [
            {
                "id": "task-existing",
                "title": "Existing UAT Topic",
                "level": "P5",
                "mode": "PRACTICE",
            }
        ]
        self.assignments: list[dict[str, str]] = []

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, bytes]:
        if method == "GET" and path == "/api/teacher/classes":
            return 200, envelope({"classes": self.classes})
        if method == "GET" and path == "/api/teacher/rubrics":
            return 200, envelope({"rubrics": self.rubrics})
        if method == "POST" and path == "/api/teacher/rubrics":
            assert payload is not None
            rubric = {**payload, "id": f"rubric-{payload['level'].lower()}"}
            self.rubrics.append(rubric)
            return 200, envelope({"rubric": rubric})
        if method == "GET" and path == "/api/teacher/tasks":
            return 200, envelope({"tasks": self.tasks})
        if method == "POST" and path == "/api/teacher/tasks":
            assert payload is not None
            task = {**payload, "id": f"task-{len(self.tasks) + 1}"}
            self.tasks.append(task)
            return 200, envelope({"task": task})
        if method == "POST" and path.startswith("/api/teacher/tasks/") and path.endswith("/assignments"):
            assert payload is not None
            task_id = path.split("/")[4]
            assignment = {
                "id": f"assignment-{task_id}",
                "task_id": task_id,
                "class_id": payload["class_id"],
                "class_name": "P5A",
            }
            self.assignments.append(assignment)
            return 200, envelope({"assignment": assignment})
        return 404, b'{"success": false}'


def test_normalize_topic_sets_exam_duration_and_practice_rules() -> None:
    practice = apply_uat_fixtures.normalize_topic(
        {
            "topic_title": "A Helpful Friend",
            "level": "p5",
            "mode": "practice",
            "instruction": "Write a story.",
        }
    )
    exam = apply_uat_fixtures.normalize_topic(
        {
            "topic_title": "A Rainy Day",
            "level": "P6",
            "mode": "EXAM",
            "instruction": "Write under exam conditions.",
            "exam_duration_minutes": 60,
        }
    )

    assert practice["level"] == "P5"
    assert practice["mode"] == "PRACTICE"
    assert "exam_duration_minutes" not in practice
    assert exam["exam_duration_minutes"] == 60


def test_apply_writing_fixtures_creates_reuses_skips_and_writes_evidence(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    (fixture_dir / "writing-fixtures.json").write_text(
        json.dumps(
            {
                "writing_topics": [
                    {
                        "topic_title": "New UAT Topic",
                        "level": "P5",
                        "mode": "PRACTICE",
                        "instruction": "Write about a school picnic.",
                        "word_minimum": 80,
                        "word_maximum": 160,
                    },
                    {
                        "topic_title": "Existing UAT Topic",
                        "level": "P5",
                        "mode": "PRACTICE",
                        "instruction": "Write about your best lesson.",
                    },
                    {
                        "topic_title": "Unassigned UAT Topic",
                        "level": "P6",
                        "mode": "EXAM",
                        "instruction": "Write under timed conditions.",
                        "exam_duration_minutes": 45,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    session = FakeApiSession()

    result = apply_uat_fixtures.apply_writing_fixtures(session, fixture_dir)

    assert [row["title"] for row in result["created_tasks"]] == ["New UAT Topic"]
    assert [row["title"] for row in result["reused_tasks"]] == ["Existing UAT Topic"]
    assert result["skipped_topics"] == [
        {
            "title": "Unassigned UAT Topic",
            "level": "P6",
            "reason": "Teacher is not assigned to P6A.",
        }
    ]
    assert result["rubric_ids_by_level"] == {"P5": "rubric-p5"}
    assert len(session.assignments) == 2
    written = json.loads((fixture_dir / "writing-fixtures.applied.json").read_text(encoding="utf-8"))
    assert written["source"].endswith("writing-fixtures.json")
