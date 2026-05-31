from datetime import datetime
from pydantic import BaseModel, Field


class DataSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_type: str = Field(min_length=1, max_length=50)
    connection_config: str | None = None
    description: str | None = None


class DataSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    connection_config: str | None = None
    description: str | None = None


class DataSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    connection_config: str | None = None
    description: str | None = None
    status: str
    last_scan_at: datetime | None = None
    total_tables: int
    total_fields: int
    is_active: bool
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScanTaskResponse(BaseModel):
    id: int
    datasource_id: int
    scan_type: str
    status: str
    total_objects: int
    processed_objects: int
    new_fields: int
    updated_fields: int
    error_log: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectionTestResult(BaseModel):
    success: bool
    message: str
