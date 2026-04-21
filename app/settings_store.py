from typing import Optional

from sqlmodel import select

from app.db import get_session
from app.models import Setting

LINE_TOKEN_KEY = "line_channel_access_token"
LINE_SECRET_KEY = "line_channel_secret"


def get_value(key: str) -> Optional[str]:
    with get_session() as s:
        row = s.get(Setting, key)
        return row.value if row and row.value else None


def set_value(key: str, value: str) -> None:
    with get_session() as s:
        row = s.get(Setting, key)
        if row:
            row.value = value
            s.add(row)
        else:
            s.add(Setting(key=key, value=value))
        s.commit()


def get_line_token() -> Optional[str]:
    return get_value(LINE_TOKEN_KEY)


def get_line_secret() -> Optional[str]:
    return get_value(LINE_SECRET_KEY)


def is_configured() -> bool:
    return bool(get_line_token()) and bool(get_line_secret())
