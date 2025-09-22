import csv
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Iterable

from loguru import logger

from aztec_monitor import (
    AztecBrowser,
    Balance,
    CoreBrowser,
    CsvAccount,
    Telegram,
    add_logger,
    read_csv,
)
from aztec_monitor.constants import DENOMINATION
from user_data.config import settings


def save_report(report_file: Path, acc: CsvAccount, data: dict) -> None:
    file_exists = report_file.exists()

    with report_file.open("a", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "id",
            "address",
            "ip",
            "port",
            "note",
            "version",
            "status",
            "sync_latest",
            "balance",
            "rewards",
            "attestations_missed",
            "attestations_succeeded",
            "attestation_success",
            "block_missed",
            "block_mined",
            "block_proposed",
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        row = {
            "id": acc.id,
            "address": acc.address,
            "ip": acc.ip,
            "port": acc.port,
            "note": acc.note or "",
            "status": data.get("status", ""),
            "version": data.get("version", "v0.0.0"),
            "sync_latest": data.get("sync_latest", 0),
            "balance": data.get("balance", 0),
            "rewards": data.get("rewards", 0),
            "attestations_missed": data.get("attestations_missed", 0),
            "attestations_succeeded": data.get("attestations_succeeded", 0),
            "attestation_success": data.get("attestation_success", 0),
            "block_missed": data.get("block_missed", 0),
            "block_mined": data.get("block_mined", 0),
            "block_proposed": data.get("block_proposed", 0),
        }

        writer.writerow(row)


def main_checker(
    acc: CsvAccount,
    explorer_browser: AztecBrowser,
    server_browser: AztecBrowser,
    telegram: Telegram | None,
    latest_explorer_block: int,
) -> dict:
    acc_report = {
        "status": "",
        "version": "",
        "sync_latest": 0,
        "balance": 0,
        "rewards": 0,
        "attestations_missed": 0,
        "attestations_succeeded": 0,
        "attestation_success": 0,
        "block_missed": 0,
        "block_mined": 0,
        "block_proposed": 0,
    }

    server_block_r = server_browser.get_server_block_req(ip=acc.ip, port=acc.port)
    if not server_block_r:
        logger.error(f"#{acc.id} | {acc.address} | can't connect to {acc.ip}:{acc.port}.")
        acc_report.update({"status": "connection_refused"})
        if settings.telegram.enabled and telegram:
            telegram.send_alarm(
                head=f"{acc.ip} | {acc.note}",
                body="can't get the latest block.",
                dashtec=f"https://dashtec.xyz/validators/{acc.address}",
                sepoliascan=f"https://sepolia.etherscan.io/address/{acc.address}",
            )
        return acc_report

    acc_report["sync_latest"] = server_block_r.result.latest.number

    node_version = server_browser.get_version_req(ip=acc.ip, port=acc.port)
    acc_report["version"] = node_version

    if (
        latest_explorer_block
        and server_block_r.result.latest.number + 3 < latest_explorer_block
    ):
        logger.warning(
            f"#{acc.id} | {acc.address} | "
            f"explorer height: {latest_explorer_block}, but the node is on {server_block_r.result.latest.number}."
        )
        acc_report.update({"status": "synced_out"})
        if settings.telegram.enabled and telegram:
            telegram.send_alarm(
                head=f"{acc.ip} | {acc.note}",
                body=(
                    f"explorer height: {latest_explorer_block}\n"
                    f"node height: {server_block_r.result.latest.number}"
                ),
                dashtec=f"https://dashtec.xyz/validators/{acc.address}",
                sepoliascan=f"https://sepolia.etherscan.io/address/{acc.address}",
            )
        return acc_report

    dashtec_r = explorer_browser.get_dashtec_req(address=acc.address)
    if not dashtec_r:
        logger.warning(
            f"#{acc.id} | {acc.address} | can't get info about validator from dashtec."
        )
        return acc_report

    if dashtec_r.balance:
        balance_value = dashtec_r.balance
        unclaimed_rewards = dashtec_r.unclaimedRewards or 0
        balance = Balance(int=balance_value, float=round(balance_value / DENOMINATION, 2))
        rewards = Balance(int=unclaimed_rewards, float=round(unclaimed_rewards / DENOMINATION, 2))

        attestations_missed = dashtec_r.totalAttestationsMissed or 0
        attestations_succeeded = dashtec_r.totalAttestationsSucceeded or 0

        blocks_missed = dashtec_r.totalBlocksMissed or 0
        blocks_mined = dashtec_r.totalBlocksMined or 0
        blocks_proposed = dashtec_r.totalBlocksProposed or 0

        acc_report.update(
            {
                "status": dashtec_r.status.lower(),
                "balance": balance.float,
                "rewards": rewards.float,
                "attestations_missed": attestations_missed,
                "attestations_succeeded": attestations_succeeded,
                "attestation_success": dashtec_r.attestationSuccess,
                "block_missed": blocks_missed,
                "block_mined": blocks_mined,
                "block_proposed": blocks_proposed,
            }
        )

        log = (
            f"#{acc.id} | {acc.address} | {node_version} | status: {dashtec_r.status.lower()} | "
            f"sync (e/s): {latest_explorer_block}/{server_block_r.result.latest.number} | "
            f"balance (r): {balance.float} $STK ({rewards.float}), "
            f"attestations (m/s): "
            f"{attestations_missed}/{attestations_succeeded} ({dashtec_r.attestationSuccess}), "
            f"blocks (m/s/p): "
            f"{blocks_missed}/{blocks_mined}/{blocks_proposed}."
        )

        total_attestations = attestations_missed + attestations_succeeded
        if total_attestations:
            attestation_success_rate = round(
                attestations_succeeded / total_attestations * 100, 2
            )
            if (
                attestation_success_rate
                < settings.monitoring.attestation_success_threshold
            ):
                logger.error(log)
                if settings.telegram.enabled and telegram:
                    telegram.send_alarm(
                        head=f"{acc.ip} | {acc.note}",
                        body=(
                            "low attestation success: "
                            f"{attestations_succeeded}/{total_attestations} "
                            f"({attestation_success_rate}%)\n"
                        ),
                        dashtec=f"https://dashtec.xyz/validators/{acc.address}",
                        sepoliascan=f"https://sepolia.etherscan.io/address/{acc.address}",
                    )
                return acc_report

        logger.blue(log)
        return acc_report

    if dashtec_r.status == "not_found":
        queue_r = explorer_browser.get_queue_req(address=acc.address)
        if queue_r:
            status = f"#{queue_r}" if queue_r != "not_registered" else queue_r
            acc_report.update({"status": status})
            if queue_r == "not_registered":
                logger.error(
                    f"#{acc.id} | {acc.address} | {node_version} | status: {status} | "
                    f"sync (e/s): {latest_explorer_block}/{server_block_r.result.latest.number}."
                )
            else:
                logger.success(
                    f"#{acc.id} | {acc.address} | {node_version} | status: {status} | "
                    f"sync (e/s): {latest_explorer_block}/{server_block_r.result.latest.number}."
                )
        return acc_report

    if dashtec_r.status.lower() in {"exiting", "zombie"}:
        acc_report.update({"status": dashtec_r.status.lower()})
        logger.error(f"#{acc.id} | {acc.address} | {node_version} | status: {dashtec_r.status.lower()}.")
        if settings.telegram.enabled and telegram:
            telegram.send_alarm(
                head=f"{acc.ip} | {acc.note}",
                body="status: exited.\n",
                dashtec=f"https://dashtec.xyz/validators/{acc.address}",
                sepoliascan=f"https://sepolia.etherscan.io/address/{acc.address}",
            )
    return acc_report


def _build_core(proxy: str | None) -> CoreBrowser:
    return CoreBrowser(
        proxy=proxy,
        request_timeout=settings.monitoring.requests.timeout,
        delay_between_requests=settings.monitoring.requests.delay_between_requests,
    )


def _build_external_browser() -> AztecBrowser:
    return AztecBrowser(
        core=_build_core(settings.monitoring.proxy.url),
        api_base_url=settings.monitoring.api.base_url,
        validator_endpoint=settings.monitoring.api.endpoint,
    )


def _build_server_browser() -> AztecBrowser:
    return AztecBrowser(
        core=_build_core(None),
        api_base_url=settings.monitoring.api.base_url,
        validator_endpoint=settings.monitoring.api.endpoint,
    )


def _format_report_path(timestamp: str) -> Path:
    template = settings.monitoring.report.output_file
    path = Path(template.format(timestamp=timestamp))
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _fetch_latest_explorer_block() -> int:
    try:
        browser = _build_external_browser()
        explorer_block = browser.get_explorer_block_req()
        if explorer_block:
            return int(explorer_block.get("height", 0))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"unable to fetch explorer block height: {exc}")
    return 0


def _monitor_accounts(
    accounts: Iterable[CsvAccount],
    telegram: Telegram | None,
    latest_explorer_block: int,
    report_file: Path,
) -> None:
    def worker(account: CsvAccount) -> tuple[CsvAccount, dict]:
        try:
            external_browser = _build_external_browser()
            server_browser = _build_server_browser()
            report = main_checker(
                acc=account,
                explorer_browser=external_browser,
                server_browser=server_browser,
                telegram=telegram,
                latest_explorer_block=latest_explorer_block,
            )
            return account, report
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception(exc)
            return account, {}

    with ThreadPoolExecutor(max_workers=settings.monitoring.threads) as executor:
        for account, report in executor.map(worker, accounts):
            save_report(report_file=report_file, acc=account, data=report)


def _sleep_between_cycles() -> None:
    if not settings.monitoring.cycle.enabled:
        return
    sleep_seconds = settings.monitoring.cycle.sleep_minutes * 60
    if sleep_seconds <= 0:
        return
    logger.info(f"sleep {round(sleep_seconds, 2)} sec | after loop.")
    time.sleep(sleep_seconds)


def _should_continue(cycle: int) -> bool:
    if not settings.monitoring.cycle.enabled:
        return False
    if settings.monitoring.cycle.max_cycles == 0:
        return True
    return cycle < settings.monitoring.cycle.max_cycles


if __name__ == "__main__":
    add_logger()
    accounts = read_csv(settings.monitoring.accounts_file)

    telegram: Telegram | None = None
    if (
        settings.telegram.enabled
        and settings.telegram.bot_api_token
        and settings.telegram.chat_id
    ):
        telegram = Telegram(
            bot_api_token=settings.telegram.bot_api_token,
            alarm_chat_id=settings.telegram.chat_id,
            timeout=settings.monitoring.requests.timeout,
            thread_id=settings.telegram.thread_id,
        )

    cycle = 0
    while True:
        try:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            report_file = _format_report_path(timestamp)
            latest_explorer_block = _fetch_latest_explorer_block()

            _monitor_accounts(
                accounts=accounts,
                telegram=telegram,
                latest_explorer_block=latest_explorer_block,
                report_file=report_file,
            )

            cycle += 1
            if not _should_continue(cycle):
                break
            _sleep_between_cycles()
        except KeyboardInterrupt:
            break
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception(exc)
