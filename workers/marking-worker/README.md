# Marking Worker

The local worker is implemented as the FastAPI package module:

```bash
python -m app.workers.marking_worker
```

Docker Compose runs it as the `marking-worker` service. It consumes Redis queue items from
`MARKING_QUEUE_NAME`, loads the corresponding `marking_results` row and calls the shared
`process_marking_result` service.

The worker uses the configured real LLM adapter. Marking requires `LLM_PROVIDER`, `LLM_MODEL` and `LLM_API_KEY`.
