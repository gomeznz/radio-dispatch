"""Shared data models for radio traffic and dispatch replies."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Priority(str, Enum):
    ROUTINE = "routine"
    PRIORITY = "priority"
    EMERGENCY = "emergency"


class UnitStatus(str, Enum):
    AVAILABLE = "available"
    ENROUTE = "enroute"
    ONSCENE = "onscene"
    BUSY = "busy"
    TRANSPORTING = "transporting"
    OUT_OF_SERVICE = "out_of_service"
    UNKNOWN = "unknown"


class TrafficIn(BaseModel):
    transcript: str = Field(min_length=1, max_length=2000)
    caller: Optional[str] = None
    channel: str = "Primary"


class DispatchReply(BaseModel):
    transcript: str
    response: str
    spoken_response: str
    intent: str
    priority: Priority
    unit_id: Optional[str] = None
    unit_status: Optional[UnitStatus] = None
    incident_type: Optional[str] = None
    location: Optional[str] = None
    log_id: int
    timestamp: datetime


class LogEntry(BaseModel):
    id: int
    timestamp: datetime
    channel: str
    direction: str
    unit_id: Optional[str]
    transcript: str
    response: str
    intent: str
    priority: Priority
    incident_type: Optional[str]
    location: Optional[str]


class UnitState(BaseModel):
    unit_id: str
    status: UnitStatus
    last_location: Optional[str] = None
    last_heard: datetime
    notes: Optional[str] = None


class StatusBoard(BaseModel):
    units: list[UnitState]
    updated_at: datetime


class SystemStatus(BaseModel):
    listening: bool = False
    channel: str = "Primary"
    message: str = "Ready"
