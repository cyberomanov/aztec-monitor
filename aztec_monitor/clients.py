"""HTTP clients used by the application."""

from __future__ import annotations

import json
import re
import time
from typing import Any

import requests
import tls_client
from fake_useragent import UserAgent

from .models import DashtecResponse, LatestBlockResponse, TelegramResponse
from .utils import retry


class CoreBrowser:
    """Wrapper around :mod:`tls_client` with sane defaults."""

    def __init__(
        self,
        proxy: str | None = None,
        request_timeout: float | None = None,
        delay_between_requests: float = 0.0,
    ):
        self.proxy = proxy
        self.session = self._init_session()
        self.request_timeout = request_timeout
        self.delay_between_requests = delay_between_requests

    def _init_session(self) -> tls_client.Session:
        session = tls_client.Session(
            client_identifier="safari_16_0",
            random_tls_extension_order=True,
        )

        if self.proxy and self.proxy not in {"http://log:pass@ip:port", "socks5://log:pass@ip:port"}:
            session.proxies = {
                "http": self.proxy,
                "https": self.proxy,
            }

        session.headers.update(
            {
                "User-Agent": UserAgent(browsers=["Safari"], os=["Mac OS X"]).random,
            }
        )
        return session

    def update_headers(self, headers: dict[str, str]) -> None:
        self.session.headers.update(headers)

    def process_request(
        self,
        url: str,
        payload: dict[str, Any] | None = None,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        return_type: str = "content",
        allow_redirects: bool = False,
    ) -> Any:
        local_headers = self.session.headers.copy()
        if headers:
            local_headers.update(headers)

        method_lower = method.lower()
        request_kwargs = {}
        if self.request_timeout is not None:
            request_kwargs["timeout_seconds"] = self.request_timeout

        if method_lower == "get":
            response = self.session.get(
                url=url,
                headers=local_headers,
                allow_redirects=allow_redirects,
                **request_kwargs,
            )
        elif method_lower == "post":
            response = self.session.post(
                url=url,
                json=payload,
                headers=local_headers,
                **request_kwargs,
            )
        elif method_lower == "options":
            response = self.session.options(
                url=url,
                json=payload,
                headers=local_headers,
                **request_kwargs,
            )
        else:
            raise ValueError("unsupported HTTP method")

        if self.delay_between_requests:
            time.sleep(self.delay_between_requests)

        if return_type == "content":
            return json.loads(response.content) if response.content else {}
        if return_type == "url":
            return response.url
        if return_type == "headers":
            return response.headers
        if return_type in {"html", "text"}:
            return response.text
        return None


class AztecBrowser:
    """High level API client for Aztec resources."""

    def __init__(
        self,
        core: CoreBrowser,
        api_base_url: str | None = None,
        validator_endpoint: str | None = None,
    ):
        self._core = core
        self._api_base_url = (api_base_url or "https://dashtec.xyz/api").rstrip("/")
        self._validator_endpoint = validator_endpoint or "/validators/{validator_address}"

    def _build_url(self, endpoint: str) -> str:
        return f"{self._api_base_url}/{endpoint.lstrip('/')}"

    @retry(module="aztec: get_server_block_req")
    def get_server_block_req(self, ip: str, port: int) -> LatestBlockResponse:
        payload = {
            "jsonrpc": "2.0",
            "method": "node_getL2Tips",
            "params": [],
            "id": 67,
        }
        response = self._core.process_request(method="POST", url=f"http://{ip}:{port}", payload=payload)
        if response and response.get("result"):
            return LatestBlockResponse(**response)
        raise RuntimeError(f"can't get the latest block: {response}")

    @retry(module="aztec: get_version_req")
    def get_version_req(self, ip: str, port: int) -> str:
        payload = {
            "jsonrpc": "2.0",
            "method": "node_getNodeInfo",
            "params": [],
            "id": 67,
        }
        response = self._core.process_request(method="POST", url=f"http://{ip}:{port}", payload=payload)
        if response and response.get("result"):
            node_version = response.get("result").get("nodeVersion")
            return f"v{node_version}" if node_version else "v0.0.0"
        raise RuntimeError(f"can't get node version: {response}")

    @retry(module="aztec: get_dashtec_req")
    def get_dashtec_req(self, address: str) -> DashtecResponse:
        url = self._build_url(self._validator_endpoint.format(validator_address=address))
        response = self._core.process_request(method="GET", url=url)
        if response and response.get("index"):
            return DashtecResponse(**response)
        if response.get("error") == "Validator not found.":
            return DashtecResponse(status="not_found")
        raise RuntimeError(f"can't get validator dashtec: {response}")

    @retry(module="aztec: get_explorer_block_req")
    def get_explorer_block_req(self) -> dict[str, Any]:
        response = self._core.process_request(
            method="GET",
            url="https://api.testnet.aztecscan.xyz/v1/temporary-api-key/l2/ui/blocks-for-table",
        )
        if response:
            return response[0]
        raise RuntimeError(f"can't get explorer block: {response}")

    @retry(module="aztec: get_queue_req")
    def get_queue_req(self, address: str) -> str | int:
        queue_url = self._build_url("validators/queue")
        response = self._core.process_request(
            method="GET",
            url=f"{queue_url}?page=1&limit=10&search={address}",
        )
        if response and response.get("validatorsInQueue"):
            return response.get("validatorsInQueue")[0].get("position", 999_999)
        if response and not response.get("validatorsInQueue"):
            return "not_registered"
        raise RuntimeError(f"can't get validator queue position: {response}")


def _escape_markdown_v2(text: str) -> str:
    return re.sub(r"([_*\\[\\]()~`>#+-=|{}.!])", r"\\\\\1", text)


class Telegram:
    """Wrapper around the Telegram HTTP API."""

    def __init__(
        self,
        bot_api_token: str,
        alarm_chat_id: str,
        *,
        timeout: float | None = None,
        thread_id: int | None = None,
    ):
        self.bot_api_token = bot_api_token
        self.alarm_chat_id = alarm_chat_id
        self.timeout = timeout
        self.thread_id = thread_id

    def _send_message(
        self, text: str, chat_id: str, parse_mode: str = "MarkdownV2"
    ) -> TelegramResponse:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        if self.thread_id is not None:
            payload["message_thread_id"] = self.thread_id

        response = requests.post(
            f"https://api.telegram.org/bot{self.bot_api_token}/sendMessage",
            json=payload,
            timeout=self.timeout,
        ).json()
        return TelegramResponse.parse_obj(response)

    def send_alarm(self, head: str, body: str, dashtec: str, sepoliascan: str) -> TelegramResponse:
        head_escaped = _escape_markdown_v2(head)
        body_escaped = _escape_markdown_v2(body)
        text = (
            f"*{head_escaped}*\n\n"
            f"[DASHTEC]({dashtec}) /// [SEPOLIASCAN]({sepoliascan})\n\n"
            f"`{body_escaped}`"
        )
        return self._send_message(text=text, chat_id=self.alarm_chat_id)
