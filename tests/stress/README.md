# Stress Scripts

These scripts hit the real API. Start Docker Compose, run migrations, seed data,
and configure real auth/grammar/LLM services first.

```bash
STRESS_API_BASE_URL=http://127.0.0.1:8000 STRESS_EVIDENCE_DIR=docs/uat-evidence/2026-06-29 python tests/stress/uat_load.py
STRESS_STUDENT_CREDENTIALS_CSV=tests/fixtures/uat/minimax/stress-student-credentials.csv STRESS_API_BASE_URL=http://127.0.0.1:8000 STRESS_EVIDENCE_DIR=docs/uat-evidence/2026-06-29 python tests/stress/uat_load.py
STRESS_API_BASE_URL=http://127.0.0.1:8000 python tests/stress/login_burst.py
STRESS_TASK_ID=<practice-task-id> python tests/stress/writing_load.py
STRESS_TASK_ID=<task-id> python tests/stress/submission_burst.py
STRESS_MARKING_RESULT_IDS=<id1,id2,...> python tests/stress/marking_queue.py
STRESS_CLASS_ID=<class-id> python tests/stress/report_after_marking.py
```

Targets:

- 150 students login within 10 minutes
- 100 concurrent students writing with autosave and suggestions
- 470 students submit within 30 minutes
- 470 essays queued for marking
- Teacher generates report after marking

## UAT load runner

`uat_load.py` is the preferred controlled-pilot stress runner. It writes JSONL
evidence under `STRESS_EVIDENCE_DIR` and covers all target scenarios in one run.
When `STRESS_STUDENT_CREDENTIALS_CSV` is set, login, writing and submission
load use distinct generated student accounts instead of the seeded student.

To avoid uncontrolled paid LLM calls, pause the marking worker before queue-load
testing, verify the queue count, clear the stress queue, then restart the worker:

```bash
docker compose stop marking-worker
STRESS_API_BASE_URL=http://127.0.0.1:8000 STRESS_EVIDENCE_DIR=docs/uat-evidence/2026-06-29 python tests/stress/uat_load.py
docker compose exec -T redis redis-cli LLEN marking:jobs
docker compose exec -T redis redis-cli DEL marking:jobs
docker compose start marking-worker
```

For 470 distinct generated students:

1. Generate fixtures with `scripts/uat/generate_minimax_uat_data.py`.
2. Copy or source `tests/fixtures/uat/minimax/openauth-users.combined.env` into
   local `.env`, then restart `auth`.
3. Import generated users with `scripts/uat/apply_uat_fixtures.py --import-users`.
4. Import generated rubrics, tasks and assignments with
   `scripts/uat/apply_uat_fixtures.py --import-writing-fixtures`.
5. Run `uat_load.py` with `STRESS_STUDENT_CREDENTIALS_CSV` pointing at
   `tests/fixtures/uat/minimax/stress-student-credentials.csv`.

`apply_uat_fixtures.py --import-writing-fixtures` uses the real teacher APIs,
reuses same-title UAT tasks and same-level UAT rubrics, and skips topics for
classes the teacher is not assigned to instead of bypassing RBAC.

Use the UAT gate checker after a stress run:

```bash
python scripts/uat/check_uat_gate.py
python scripts/uat/check_uat_gate.py --require-distinct-student-stress --require-writing-fixtures-applied
```
