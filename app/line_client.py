from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)

from app.settings_store import get_line_token


class LineNotConfigured(RuntimeError):
    pass


def _api() -> MessagingApi:
    token = get_line_token()
    if not token:
        raise LineNotConfigured("LINE Channel access token 尚未設定，請到 /settings 填寫")
    config = Configuration(access_token=token)
    return MessagingApi(ApiClient(config))


def push_text(group_id: str, text: str) -> None:
    api = _api()
    api.push_message(
        PushMessageRequest(
            to=group_id,
            messages=[TextMessage(text=text)],
        )
    )
