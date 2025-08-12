import re

import requests

from datatypes.responses.telegram import TelegramResponse


def _escape_markdown_v2(text: str) -> str:
    return re.sub(r'([_*\[\]()~`>#+-=|{}.!])', r'\\\1', text)


class Telegram:
    def __init__(
            self,
            bot_api_token: str,
            alarm_chat_id: str
    ):
        self.bot_api_token = bot_api_token
        self.alarm_chat_id = alarm_chat_id

    def _send_message(self, text: str, chat_id: str, parse_mode: str = "MarkdownV2") -> TelegramResponse:
        response = requests.post(
            f"https://api.telegram.org/bot{self.bot_api_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
        ).json()
        return TelegramResponse.parse_obj(response)

    def send_alarm(self, head: str, body: str, dashboard: str) -> TelegramResponse:
        head_escaped = _escape_markdown_v2(head)
        body_escaped = _escape_markdown_v2(body)
        text = (
            f"*{head_escaped}*\n\n"
            f"[dashtec]({dashboard})\n\n"
            f"`{body_escaped}`"
        )
        return self._send_message(text=text, chat_id=self.alarm_chat_id)
