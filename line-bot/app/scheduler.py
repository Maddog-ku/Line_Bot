import logging
import random
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import select

from app.config import settings
from app.db import get_session
from app.line_client import push_text
from app.models import Message, PickMode, Schedule, SendLog, SendStatus

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone=settings.tz)


def _job_id(schedule_id: int) -> str:
    return f"schedule-{schedule_id}"


def _pick_message(session, schedule: Schedule) -> Optional[Message]:
    messages = session.exec(
        select(Message)
        .where(Message.schedule_id == schedule.id)
        .order_by(Message.order_index)
    ).all()
    if not messages:
        return None
    if schedule.pick_mode == PickMode.random:
        return random.choice(messages)
    idx = schedule.cursor % len(messages)
    picked = messages[idx]
    schedule.cursor = (idx + 1) % len(messages)
    session.add(schedule)
    return picked


def run_schedule(schedule_id: int) -> None:
    with get_session() as session:
        schedule = session.get(Schedule, schedule_id)
        if not schedule or not schedule.enabled:
            return
        message = _pick_message(session, schedule)
        if not message:
            logger.warning("Schedule %s has no messages", schedule_id)
            return
        try:
            push_text(schedule.group_id, message.content)
            session.add(SendLog(
                schedule_id=schedule.id,
                message_id=message.id,
                status=SendStatus.success,
            ))
        except Exception as e:
            logger.exception("Push failed for schedule %s", schedule_id)
            session.add(SendLog(
                schedule_id=schedule.id,
                message_id=message.id,
                status=SendStatus.failed,
                error=str(e)[:500],
            ))
        session.commit()


def register_schedule(schedule: Schedule) -> None:
    if not schedule.enabled:
        unregister_schedule(schedule.id)
        return
    trigger = CronTrigger.from_crontab(schedule.cron, timezone=settings.tz)
    scheduler.add_job(
        run_schedule,
        trigger=trigger,
        args=[schedule.id],
        id=_job_id(schedule.id),
        replace_existing=True,
        misfire_grace_time=60,
    )


def unregister_schedule(schedule_id: int) -> None:
    try:
        scheduler.remove_job(_job_id(schedule_id))
    except Exception:
        pass


def load_all_schedules() -> None:
    with get_session() as session:
        schedules = session.exec(select(Schedule).where(Schedule.enabled == True)).all()
        for s in schedules:
            try:
                register_schedule(s)
            except Exception:
                logger.exception("Failed to register schedule %s", s.id)


def start() -> None:
    if not scheduler.running:
        scheduler.start()
    load_all_schedules()


def shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
