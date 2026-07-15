import config  # noqa: F401 — load .env before AWS modules

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from careerbuilder import fetch_careerbuilder_jobs
from dice import fetch_dice_jobs
from dynamodb_store import ensure_jobs_table, put_jobs
from email_utils import format_date
from indeed import fetch_indeed_jobs
from linkedin import fetch_linkedin_jobs

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

ROOT = Path(__file__).resolve().parent
CREDENTIALS_FILE = ROOT / "credentials.json"
TOKEN_FILE = ROOT / "token.json"


SOURCE_LABELS = {
    "linkedin": "LinkedIn",
    "dice": "Dice",
    "indeed": "Indeed",
    "careerbuilder": "CareerBuilder",
}


def get_gmail_service():
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


if __name__ == "__main__":
    service = get_gmail_service()
    profile = service.users().getProfile(userId="me").execute()
    print(f"Authenticated as {profile['emailAddress']}\n")

    print("Fetching emails from the last 1 day (LinkedIn, Dice, Indeed, CareerBuilder)...\n")

    jobs = fetch_linkedin_jobs(service, max_results=50, days=1)
    jobs.extend(fetch_dice_jobs(service, max_results=50, days=1))
    jobs.extend(fetch_indeed_jobs(service, max_results=50, days=1))
    jobs.extend(fetch_careerbuilder_jobs(service, max_results=50, days=1))

    if not jobs:
        print(
            "No jobs found in today's emails for label:jobs-linkedin, label:jobs-dice, "
            "label:jobs-indeed, or label:Jobs-Careerbuilder"
        )
    else:
        by_source: dict[str, int] = {}
        for job in jobs:
            by_source[job.source] = by_source.get(job.source, 0) + 1
        print(
            "Parsed "
            + ", ".join(f"{SOURCE_LABELS.get(k, k)}={v}" for k, v in sorted(by_source.items()))
        )
        print(f"Found {len(jobs)} job listing(s):\n")
        for i, job in enumerate(jobs, start=1):
            print(f"{i}. {job.title}")
            print(f"   Job ID:   {job.job_id}")
            print(f"   Source:   {SOURCE_LABELS.get(job.source, job.source)}")
            print(f"   Status:   {job.status}")
            print(f"   Desc:     {job.job_description}")
            print(f"   Analysis: {job.analysis_status}")
            print(f"   Applied:  {job.applied}")
            print(f"   Company:  {job.company or 'n/a'}")
            print(f"   Location: {job.location or 'n/a'}")
            print(f"   Date:     {format_date(job.date)}")
            print(f"   URL:      {job.url}")
            print()

        table_name = ensure_jobs_table()
        unique_count = len({(job.job_id, job.source) for job in jobs})
        written = put_jobs(jobs, table_name=table_name)
        print(
            f"Upserted {written} unique job(s) into DynamoDB table '{table_name}' "
            f"(from {len(jobs)} parsed, {len(jobs) - unique_count} duplicates skipped). "
            "Existing jobs were kept - nothing was deleted."
        )