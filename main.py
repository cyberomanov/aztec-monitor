import csv
import os
from datetime import datetime

from loguru import logger

from datatypes.csv_account import CsvAccount
from datatypes.responses.balance import Balance
from local_data import constants
from sdk.aztec_browser import AztecBrowser
from sdk.core_browser import CoreBrowser
from sdk.telegram import Telegram
from tools.add_logger import add_logger
from tools.read_file import read_csv
from tools.sleep import sleep_in_range
from user_data import config


def save_report(report_file: str, acc: CsvAccount, data: dict):
    file_exists = os.path.exists(report_file)

    with open(report_file, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'id', 'address', 'ip', 'port', 'note',
            'status',
            'sync_latest',
            'balance', 'rewards',
            'attestations_missed', 'attestations_succeeded', 'attestation_success',
            'block_missed', 'block_mined', 'block_proposed'
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        row = {
            'id': acc.id,
            'address': acc.address,
            'ip': acc.ip,
            'port': acc.port,
            'note': acc.note or '',
            'status': data.get('status', ''),
            'sync_latest': data.get('sync_latest', 0),
            'balance': data.get('balance', 0),
            'rewards': data.get('rewards', 0),
            'attestations_missed': data.get('attestations_missed', 0),
            'attestations_succeeded': data.get('attestations_succeeded', 0),
            'attestation_success': data.get('attestation_success', 0),
            'block_missed': data.get('block_missed', 0),
            'block_mined': data.get('block_mined', 0),
            'block_proposed': data.get('block_proposed', 0)
        }

        writer.writerow(row)


def main_checker(
        acc: CsvAccount,
        explorer_browser: AztecBrowser,
        server_browser: AztecBrowser,
        telegram: Telegram
):
    acc_report = {
        'status': '',
        'sync_latest': 0,
        'balance': 0,
        'rewards': 0,
        'attestations_missed': 0,
        'attestations_succeeded': 0,
        'attestation_success': 0,
        'block_missed': 0,
        'block_mined': 0,
        'block_proposed': 0
    }

    server_block_r = server_browser.get_server_block_req(ip=acc.ip, port=acc.port)
    if not server_block_r:
        logger.error(f"#{acc.id} | {acc.address} | can't connect to {acc.ip}:{acc.port}.")
        telegram.send_alarm(
            head=f"{acc.ip} | {acc.note}",
            body="can't get the latest block.",
            dashboard=f"https://dashtec.xyz/validators/{acc.address}"
        )
        return acc_report

    acc_report['sync_latest'] = server_block_r.result.latest.number

    explorer_block_r = explorer_browser.get_explorer_block_req()
    latest_explorer_block = 0 if not explorer_block_r else int(explorer_block_r["height"])

    if server_block_r.result.latest.number + 3 < latest_explorer_block:
        logger.warning(
            f"#{acc.id} | {acc.address} | "
            f"explorer height: {latest_explorer_block}, but the node is on {server_block_r.result.latest.number}."
        )
        telegram.send_alarm(
            head=f"{acc.ip} | {acc.note}",
            body=f"explorer height: {latest_explorer_block}\nbut the node is on {server_block_r.result.latest.number}.",
            dashboard=f"https://dashtec.xyz/validators/{acc.address}"
        )
        return acc_report

    dashtec_r = explorer_browser.get_dashtec_req(address=acc.address)
    if dashtec_r.balance:
        balance = Balance(int=dashtec_r.balance, float=round(dashtec_r.balance / constants.DENOMINATION, 2))
        rewards = Balance(int=dashtec_r.balance, float=round(dashtec_r.unclaimedRewards / constants.DENOMINATION, 2))

        acc_report.update({
            'status': dashtec_r.status.lower(),
            'balance': balance.float,
            'rewards': rewards.float,
            'attestations_missed': dashtec_r.totalAttestationsMissed,
            'attestations_succeeded': dashtec_r.totalAttestationsSucceeded,
            'attestation_success': dashtec_r.attestationSuccess,
            'block_missed': dashtec_r.totalBlocksMissed,
            'block_mined': dashtec_r.totalBlocksMined,
            'block_proposed': dashtec_r.totalBlocksProposed
        })

        logger.blue(
            f"#{acc.id} | {acc.address} | status: {dashtec_r.status.lower()} | "
            f"sync (e/s): {latest_explorer_block}/{server_block_r.result.latest.number} | "
            f"balance (+r): {balance.float} $STK (+{rewards.float}), "
            f"attestations (m/s): "
            f"{dashtec_r.totalAttestationsMissed}/"
            f"{dashtec_r.totalAttestationsSucceeded} ({dashtec_r.attestationSuccess}), "
            f"blocks (m/s/p): "
            f"{dashtec_r.totalBlocksMissed}/{dashtec_r.totalBlocksMined}/{dashtec_r.totalBlocksProposed}."
        )
    elif dashtec_r.status == 'not_found':
        acc_report.update({'status': 'not_active'})
        logger.warning(f"#{acc.id} | {acc.address} | status: not active validator yet.")

    return acc_report


if __name__ == '__main__':
    add_logger()
    accs = read_csv('./user_data/accounts.csv')

    while True:
        try:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            report_file = f"user_data/reports/{timestamp}.csv"
            os.makedirs(os.path.dirname(report_file), exist_ok=True)

            explorer_browser = AztecBrowser(browser=CoreBrowser(proxy=config.mobile_proxy))
            server_browser = AztecBrowser(browser=CoreBrowser())
            telegram = Telegram(bot_api_token=config.bot_api_key, alarm_chat_id=config.alarm_chat_id)

            for acc in accs:
                acc_report = main_checker(
                    acc=acc,
                    explorer_browser=explorer_browser,
                    server_browser=server_browser,
                    telegram=telegram
                )

                save_report(report_file=report_file, acc=acc, data=acc_report)
                sleep_in_range(*config.sleep_between_accs)

            sleep_in_range(
                sec_from=config.sleep_between_loop[0],
                sec_to=config.sleep_between_loop[1],
                log="after loop"
            )

        except KeyboardInterrupt:
            exit()
        except Exception as e:
            logger.exception(e)
