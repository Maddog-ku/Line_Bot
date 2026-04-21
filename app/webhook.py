import logging

from fastapi import APIRouter, Header, HTTPException, Request
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    JoinEvent,
    MessageEvent,
    GroupSource,
)
from sqlmodel import select

from app.db import get_session
from app.models import Group
from app.settings_store import get_line_secret

logger = logging.getLogger(__name__)
router = APIRouter()


def _upsert_group(group_id: str) -> None:
    with get_session() as session:
        existing = session.exec(select(Group).where(Group.group_id == group_id)).first()
        if not existing:
            session.add(Group(group_id=group_id))
            session.commit()
            logger.info("Stored new group: %s", group_id)


@router.post("/webhook")
async def webhook(request: Request, x_line_signature: str = Header(...)):
    secret = get_line_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="LINE Channel secret 尚未設定")
    parser = WebhookParser(secret)

    body = (await request.body()).decode("utf-8")
    try:
        events = parser.parse(body, x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        source = getattr(event, "source", None)
        if isinstance(source, GroupSource):
            if isinstance(event, (JoinEvent, MessageEvent)):
                _upsert_group(source.group_id)
    return {"ok": True}
