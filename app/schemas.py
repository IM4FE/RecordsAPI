from pydantic import BaseModel, Field, field_validator
from typing import Optional
import datetime


class RecordBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=75)
    details: Optional[str] = Field(None, max_length=500)
    is_done: bool = Field(False)
    record_date: Optional[datetime.datetime] = Field(None)

    @field_validator('record_date')
    def parse_due_date(cls, value):
        if isinstance(value, str):
            try:
                return datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('Invalid datetime format')
        return value

class RecordCreate(RecordBase):
    pass

class RecordUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=75)
    details: Optional[str] = Field(None, max_length=500)
    is_done: Optional[bool] = None
    record_date: Optional[datetime.datetime] = Field(None)

    @field_validator('record_date')
    def parse_due_date(cls, value):
        if isinstance(value, str):
            try:
                return datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('Invalid datetime format')
        return value

class RecordResponse(RecordBase):
    id: int
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]

    class ConfigDict:
        from_attributes = True