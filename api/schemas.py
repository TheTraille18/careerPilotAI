from pydantic import BaseModel, Field

class Job(BaseModel):
    jobId: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    date: str = ""
    url: str = ""
    source: str = ""
    status: str = ""
    jobDescription: str = ""
    analysisStatus: str = ""
    applied: str = ""
    appliedDate: str = ""
    emailId: str = ""
    updatedAt: str = ""
    evalResult: dict | None = None
    fit: str = "Unset"
    fitReason: str = ""
    fitCheckedAt: str = ""


class JobCreate(BaseModel):
    title: str = Field(min_length=1)
    company: str = ""
    location: str = ""
    url: str = ""
    source: str = "manual"
    jobDescription: str = ""
