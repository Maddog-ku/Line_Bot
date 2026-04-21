from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class PickMode(str, Enum):
    sequential = "sequential"
    random = "random"


class SendStatus(str, Enum):
    success = "success"
    failed = "failed"


class Group(SQLModel, table=True):
    group_id: str = Field(primary_key=True)
    name: Optional[str] = None
    joined_at: datetime = Field(default_factory=datetime.utcnow)


class Schedule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    group_id: str = Field(foreign_key="group.group_id")
    cron: str
    pick_mode: PickMode = Field(default=PickMode.sequential)
    cursor: int = Field(default=0)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    schedule_id: int = Field(foreign_key="schedule.id")
    content: str
    order_index: int = Field(default=0)


class Setting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str = ""


class SendLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    schedule_id: int
    message_id: Optional[int] = None
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    status: SendStatus
    error: Optional[str] = None
