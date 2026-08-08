.PHONY: backend purge-senior-titles reconcile-applied

backend:
	.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

purge-senior-titles:
	.venv/bin/python -c "from dynamodb_store import delete_excluded_title_jobs; \
d=delete_excluded_title_jobs(); \
print(f'Deleted {len(d)} job(s)'); \
[print(f\"  - {x['title']} ({x['source']})\") for x in d]"

reconcile-applied:
	.venv/bin/python -c "from reconcile_applied import reconcile_applied; \
from pprint import pprint; \
pprint(reconcile_applied())"
