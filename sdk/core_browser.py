import json

import tls_client
from fake_useragent import UserAgent

from user_data import config


class CoreBrowser:
    def __init__(self, proxy: str = None):
        self.max_retries = config.max_retries
        self.proxy = proxy
        self.session = self.init_session()

    def init_session(self) -> tls_client.Session:
        session = tls_client.Session(
            client_identifier="safari_16_0",
            random_tls_extension_order=True
        )

        if self.proxy:
            session.proxies = {
                'http': self.proxy,
                'https': self.proxy
            }

        session.headers.update({
            "User-Agent": UserAgent(browsers=["Safari"], os=["Mac OS X"]).random,
        })

        return session

    def update_headers(self, headers: dict):
        self.session.headers.update(headers)

    def process_request(
            self,
            url: str,
            payload: dict = None,
            method: str = "GET",
            headers: dict = None,
            return_type: str = "content",
            allow_redirects: bool = False
    ) -> dict | None:

        local_headers = self.session.headers.copy()
        if headers:
            local_headers.update(headers)

        if method.lower() == 'get':
            response = self.session.get(url=url, headers=local_headers, allow_redirects=allow_redirects)
        elif method.lower() == 'post':
            response = self.session.post(url=url, json=payload, headers=local_headers)
        elif method.lower() == 'options':
            response = self.session.options(url=url, json=payload, headers=local_headers)
        else:
            raise Exception("unsupported HTTP method")

        if return_type == 'content':
            return json.loads(response.content) if response.content else {}
        elif return_type == 'url':
            return response.url
        elif return_type == 'headers':
            return response.headers
        elif return_type == 'html' or return_type == 'text':
            return response.text

        return None
