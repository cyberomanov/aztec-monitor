from datatypes.responses.dashtec import DashtecResponse
from datatypes.responses.latest_block import LatestBlockResponse
from sdk.core_browser import CoreBrowser

from tools.retrier import retry
from user_data import config


class AztecBrowser(CoreBrowser):
    def __init__(self, browser: CoreBrowser):
        self.max_retries = config.max_retries
        self.proxy = browser.proxy
        self.session = browser.session

    @retry(module="aztec: get_server_block_req")
    def get_server_block_req(self, ip: str, port: int) -> LatestBlockResponse:
        payload = {
            "jsonrpc": "2.0",
            "method": "node_getL2Tips",
            "params": [],
            "id": 67
        }
        r = self.process_request(
            method="POST",
            url=f"http://{ip}:{port}",
            payload=payload
        )

        if r and r.get('result'):
            return LatestBlockResponse(**r)
        else:
            raise Exception(f"can't get the latest block: {r}")

    @retry(module="aztec: get_dashtec_req")
    def get_dashtec_req(self, address: str) -> DashtecResponse:
        r = self.process_request(
            method="GET",
            url=f"https://dashtec.xyz/api/validators/{address}?"
        )
        if r and r.get('index'):
            return DashtecResponse(**r)
        elif r.get('error') == "Validator not found.":
            return DashtecResponse(status='not_found')
        else:
            raise Exception(f"can't get validator dashtec: {r}")

    @retry(module="aztec: get_explorer_block_req")
    def get_explorer_block_req(self) -> DashtecResponse:
        r = self.process_request(
            method="GET",
            url=f"https://api.testnet.aztecscan.xyz/v1/temporary-api-key/l2/ui/blocks-for-table"
        )
        if r:
            return r[0]
        else:
            raise Exception(f"can't get explorer block: {r}")
