from loguru import logger

from datatypes.responses.balance import Balance
from local_data import constants
from sdk.aztec_browser import AztecBrowser
from sdk.core_browser import CoreBrowser
from sdk.telegram import Telegram
from tools.add_logger import add_logger
from tools.read_file import read_csv
from tools.sleep import sleep_in_range
from user_data import config


def main(browser: AztecBrowser, telegram: Telegram):
    alarm = False

    block_r = browser.get_block_req(ip=acc.ip, port=acc.port)
    if block_r:
        dashtec_r = browser.get_dashtec_req(address=acc.address)
        if dashtec_r.balance:
            balance = Balance(
                int=dashtec_r.balance,
                float=round(dashtec_r.balance / constants.DENOMINATION, 2)
            )
            rewards = Balance(
                int=dashtec_r.balance,
                float=round(dashtec_r.unclaimedRewards / constants.DENOMINATION, 2)
            )
            logger.blue(
                f"#{acc.id} | {acc.address} | "
                f"sync: {block_r.result.latest.number}/{block_r.result.proven.number}/{block_r.result.proven.number} | "
                f"balance: {balance.float} $STK (+{rewards.float}), "
                f"attestations: {dashtec_r.totalAttestationsMissed}/{dashtec_r.totalAttestationsSucceeded} ({dashtec_r.attestationSuccess}), "
                f"blocks: {dashtec_r.totalBlocksMissed}/{dashtec_r.totalBlocksMined} ({dashtec_r.totalBlocksProposed})."
            )
        elif dashtec_r.status == 'not_found':
            logger.warning(
                f"#{acc.id} | {acc.address} | validator is not active yet."
            )
    else:
        logger.error(
            f"#{acc.id} | {acc.address} | can't connect to {acc.ip}:{acc.port}."
        )
        alarm = True

    if alarm:
        telegram.send_alarm(
            head=f"{acc.ip} | {acc.note}",
            body="can't get the latest block.",
            dashboard=f"https://dashtec.xyz/validators/{acc.address}"
        )


if __name__ == '__main__':
    add_logger()
    accs = read_csv('./user_data/accounts.csv')

    while True:
        try:
            browser = AztecBrowser(browser=CoreBrowser(proxy=config.mobile_proxy))
            telegram = Telegram(bot_api_token=config.bot_api_key, alarm_chat_id=config.alarm_chat_id)
            for acc in accs:
                main(browser=browser, telegram=telegram)
                sleep_in_range(*config.sleep_between_accs)
            sleep_in_range(*config.sleep_between_loop)

        except KeyboardInterrupt:
            exit()
        except Exception as e:
            logger.exception(e)
