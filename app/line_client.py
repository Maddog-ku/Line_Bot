from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)

from app.config import settings


def _api() -> MessagingApi:
    config = Configuration(access_token=settings.line_channel_access_token)
    return MessagingApi(ApiClient(config))


def push_text(group_id: str, text: str) -> None:
    api = _api()
    api.push_message(
        PushMessageRequest(
            to=group_id,
            messages=[TextMessage(text=text)],
        )
    )
