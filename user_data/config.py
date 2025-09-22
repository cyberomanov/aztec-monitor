"""Configuration loader for the Aztec monitor application."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, validator


CONFIG_PATH = Path(__file__).with_name("config.yaml")
EXAMPLE_PATH = Path(__file__).with_name("config-example.yaml")


class MobileProxyConfig(BaseModel):
    """Credentials for a mobile proxy endpoint."""

    scheme: str = "http"
    address: str
    port: int
    login: str
    password: str
    change_ip_url: str | None = None

    @property
    def url(self) -> str:
        return f"{self.scheme}://{self.login}:{self.password}@{self.address}:{self.port}"


class ProxyConfig(BaseModel):
    """Proxy settings for outbound requests."""

    enabled: bool = False
    mobile_proxy: MobileProxyConfig | None = None

    @property
    def url(self) -> str | None:
        if not self.enabled or not self.mobile_proxy:
            return None
        return self.mobile_proxy.url


class RequestsConfig(BaseModel):
    """HTTP client behaviour."""

    timeout: float = 30.0
    retries: int = 1
    delay_between_requests: float = Field(default=0.0, ge=0.0)


class ApiConfig(BaseModel):
    """Dashtec API settings."""

    base_url: str = "https://dashtec.xyz/api"
    endpoint: str = "/validators/{validator_address}"


class ReportConfig(BaseModel):
    """Report generation settings."""

    output_file: str = "user_data/reports/{timestamp}.csv"


class CycleConfig(BaseModel):
    """Continuous monitoring behaviour."""

    enabled: bool = True
    sleep_minutes: float = Field(default=15.0, ge=0.0)
    max_cycles: int = Field(default=0, ge=0)


class MonitoringConfig(BaseModel):
    """Top level monitoring configuration."""

    threads: int = Field(default=1, ge=1)
    proxy: ProxyConfig = ProxyConfig()
    requests: RequestsConfig = RequestsConfig()
    api: ApiConfig = ApiConfig()
    report: ReportConfig = ReportConfig()
    cycle: CycleConfig = CycleConfig()
    attestation_success_threshold: float = Field(default=90.0, ge=0.0, le=100.0)
    accounts_file: str = "user_data/accounts.csv"

    @validator("threads", pre=True, always=True)
    def _ensure_threads(cls, value: Any) -> int:
        threads = int(value or 1)
        return threads if threads > 0 else 1


class TelegramConfig(BaseModel):
    """Telegram notification settings."""

    enabled: bool = False
    bot_api_token: str = ""
    chat_id: str = ""
    thread_id: int | None = None


class Settings(BaseModel):
    """Complete application configuration."""

    monitoring: MonitoringConfig = MonitoringConfig()
    telegram: TelegramConfig = TelegramConfig()


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):  # pragma: no cover - defensive
        raise ValueError("configuration root must be a mapping")
    return data


def _load_settings() -> Settings:
    if CONFIG_PATH.exists():
        data = _load_yaml(CONFIG_PATH)
    else:
        if not EXAMPLE_PATH.exists():
            raise FileNotFoundError("configuration file is missing")
        data = _load_yaml(EXAMPLE_PATH)
    return Settings.parse_obj(data)


settings = _load_settings()

__all__ = ["settings", "Settings"]

