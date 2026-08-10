from aiapply import fetch_aiapply_confirmations
from dynamodb_store import ensure_jobs_table, put_jobs
from gmail import SOURCE_LABELS, get_gmail_service
from mcp.server.mcpserver import MCPServer
from reconcile_applied import reconcile_applied

server = MCPServer("careerpilot-gmail", version="0.1.0")


@server.tool(description="List CareerPilot job email sources / Gmail labels")
def list_job_sources() -> str:
    lines = [f"{key}: {label}" for key, label in SOURCE_LABELS.items()]
    return "\n".join(lines)


@server.tool(
    description=(
        "Fetch NEW AIApply confirmation emails (skips email ids already in DynamoDB), "
        "extract title/company with Bedrock once, upsert Applied aiapply rows, "
        "then mark matching LinkedIn/Dice/Indeed/etc listings as Applied"
    )
)
def sync_job_gmails(days: int = 5, max_results: int = 50) -> str:
    service = get_gmail_service()
    table_name = ensure_jobs_table()

    jobs = fetch_aiapply_confirmations(
        service,
        max_results=max_results,
        days=days,
        skip_existing=True,
    )

    written = 0
    if jobs:
        written = put_jobs(jobs, table_name=table_name)

    result = reconcile_applied(table_name=table_name)

    by_company = {}
    for job in jobs:
        by_company[job.company] = by_company.get(job.company, 0) + 1
    detail = (
        ", ".join(f"{company} ({count})" for company, count in sorted(by_company.items()))
        or "none"
    )

    match_lines = [
        f"  - [{m['source']}] {m['company']} | {m['title']}" for m in result["matches"][:20]
    ]
    matches_text = "\n".join(match_lines) if match_lines else "  (none)"

    return (
        f"New AIApply extractions: {len(jobs)} (upserted {written}). Companies: {detail}\n"
        f"Reconcile: {result['aiapplyApplications']} aiapply apps, "
        f"{result['listingsChecked']} listings checked, "
        f"{result['markedApplied']} newly marked Applied, "
        f"{result['alreadyApplied']} already Applied.\n"
        f"Newly marked:\n{matches_text}"
    )


@server.tool(
    description=(
        "Mark LinkedIn/Dice/Indeed/CareerBuilder/RemoteRocketship listings as Applied "
        "when title+company match an AIApply application (no Bedrock, no Gmail)"
    )
)
def reconcile_applied_jobs() -> str:
    table_name = ensure_jobs_table()
    result = reconcile_applied(table_name=table_name)
    match_lines = [
        f"  - [{m['source']}] {m['company']} | {m['title']}" for m in result["matches"][:50]
    ]
    matches_text = "\n".join(match_lines) if match_lines else "  (none)"
    return (
        f"AIApply applications: {result['aiapplyApplications']}\n"
        f"Listings checked: {result['listingsChecked']}\n"
        f"Newly marked Applied: {result['markedApplied']}\n"
        f"Already Applied matches: {result['alreadyApplied']}\n"
        f"Newly marked:\n{matches_text}"
    )


if __name__ == "__main__":
    server.run(transport="stdio")
