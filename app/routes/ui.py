from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app import scheduler as sched
from app.db import get_session
from app.line_client import push_text
from app.models import Group, Message, PickMode, Schedule, SendLog
from app import settings_store

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def session_dep():
    with get_session() as s:
        yield s


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    if not settings_store.is_configured():
        return RedirectResponse(url="/settings", status_code=303)
    return RedirectResponse(url="/schedules", status_code=303)


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    token = settings_store.get_line_token() or ""
    secret = settings_store.get_line_secret() or ""
    saved = request.query_params.get("saved") == "1"
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "has_token": bool(token),
            "has_secret": bool(secret),
            "token_masked": _mask(token),
            "secret_masked": _mask(secret),
            "saved": saved,
        },
    )


@router.post("/settings")
def save_settings(
    line_channel_access_token: str = Form(""),
    line_channel_secret: str = Form(""),
):
    token = line_channel_access_token.strip()
    secret = line_channel_secret.strip()
    if token:
        settings_store.set_value(settings_store.LINE_TOKEN_KEY, token)
    if secret:
        settings_store.set_value(settings_store.LINE_SECRET_KEY, secret)
    return RedirectResponse(url="/settings?saved=1", status_code=303)


@router.get("/groups", response_class=HTMLResponse)
def groups_page(request: Request, s: Session = Depends(session_dep)):
    groups = s.exec(select(Group).order_by(Group.joined_at.desc())).all()
    return templates.TemplateResponse("groups.html", {"request": request, "groups": groups})


@router.post("/groups/{group_id}/rename")
def rename_group(group_id: str, name: str = Form(""), s: Session = Depends(session_dep)):
    g = s.get(Group, group_id)
    if not g:
        raise HTTPException(404)
    g.name = name or None
    s.add(g)
    s.commit()
    return RedirectResponse(url="/groups", status_code=303)


@router.get("/schedules", response_class=HTMLResponse)
def schedules_page(request: Request, s: Session = Depends(session_dep)):
    if not settings_store.is_configured():
        return RedirectResponse(url="/settings", status_code=303)
    schedules = s.exec(select(Schedule).order_by(Schedule.id.desc())).all()
    groups = s.exec(select(Group)).all()
    group_map = {g.group_id: g for g in groups}
    return templates.TemplateResponse(
        "schedules.html",
        {"request": request, "schedules": schedules, "groups": groups, "group_map": group_map},
    )


@router.post("/schedules")
def create_schedule(
    name: str = Form(...),
    group_id: str = Form(...),
    cron: str = Form(...),
    pick_mode: PickMode = Form(PickMode.sequential),
    s: Session = Depends(session_dep),
):
    schedule = Schedule(name=name, group_id=group_id, cron=cron, pick_mode=pick_mode)
    s.add(schedule)
    s.commit()
    s.refresh(schedule)
    sched.register_schedule(schedule)
    return RedirectResponse(url="/schedules", status_code=303)


@router.post("/schedules/{sid}/toggle")
def toggle_schedule(sid: int, s: Session = Depends(session_dep)):
    schedule = s.get(Schedule, sid)
    if not schedule:
        raise HTTPException(404)
    schedule.enabled = not schedule.enabled
    s.add(schedule)
    s.commit()
    s.refresh(schedule)
    if schedule.enabled:
        sched.register_schedule(schedule)
    else:
        sched.unregister_schedule(sid)
    return RedirectResponse(url="/schedules", status_code=303)


@router.post("/schedules/{sid}/delete")
def delete_schedule(sid: int, s: Session = Depends(session_dep)):
    schedule = s.get(Schedule, sid)
    if not schedule:
        raise HTTPException(404)
    s.exec(select(Message).where(Message.schedule_id == sid))
    for m in s.exec(select(Message).where(Message.schedule_id == sid)).all():
        s.delete(m)
    s.delete(schedule)
    s.commit()
    sched.unregister_schedule(sid)
    return RedirectResponse(url="/schedules", status_code=303)


@router.post("/schedules/{sid}/test")
def test_schedule(sid: int):
    sched.run_schedule(sid)
    return RedirectResponse(url="/logs", status_code=303)


@router.get("/schedules/{sid}/messages", response_class=HTMLResponse)
def messages_page(sid: int, request: Request, s: Session = Depends(session_dep)):
    schedule = s.get(Schedule, sid)
    if not schedule:
        raise HTTPException(404)
    messages = s.exec(
        select(Message).where(Message.schedule_id == sid).order_by(Message.order_index)
    ).all()
    return templates.TemplateResponse(
        "messages.html",
        {"request": request, "schedule": schedule, "messages": messages},
    )


@router.post("/schedules/{sid}/messages")
def create_message(sid: int, content: str = Form(...), s: Session = Depends(session_dep)):
    existing = s.exec(select(Message).where(Message.schedule_id == sid)).all()
    next_idx = max((m.order_index for m in existing), default=-1) + 1
    s.add(Message(schedule_id=sid, content=content, order_index=next_idx))
    s.commit()
    return RedirectResponse(url=f"/schedules/{sid}/messages", status_code=303)


@router.post("/messages/{mid}/delete")
def delete_message(mid: int, s: Session = Depends(session_dep)):
    m = s.get(Message, mid)
    if not m:
        raise HTTPException(404)
    sid = m.schedule_id
    s.delete(m)
    s.commit()
    return RedirectResponse(url=f"/schedules/{sid}/messages", status_code=303)


@router.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request, s: Session = Depends(session_dep)):
    logs = s.exec(select(SendLog).order_by(SendLog.sent_at.desc()).limit(100)).all()
    return templates.TemplateResponse("logs.html", {"request": request, "logs": logs})
