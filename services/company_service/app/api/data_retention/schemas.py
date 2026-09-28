from pydantic import BaseModel, Field


class DataPurgeRequest(BaseModel):
    months: int = Field(default=6, ge=1, le=120)


class DataPurgeResponseSchema(BaseModel):
    purged_count: int
