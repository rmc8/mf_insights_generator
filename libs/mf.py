import io
import time
import re
from urllib.parse import urljoin

import httpx
import pandas as pd
from bs4 import BeautifulSoup

from playwright.sync_api import (
    sync_playwright,
    Page,
    Browser,
    BrowserContext,
    Playwright,
)


class MoneyForwardMeClient:
    BASE_URL = "https://moneyforward.com"
    session = httpx.Client()

    def __init__(
        self,
        email: str,
        password: str,
        ua: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    ):
        self.email = email
        self.password = password
        self.headers = {"User-Agent": ua}
        self.page: Page | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.playwright: Playwright | None = None

    def build_url(self, path: str) -> str:
        return urljoin(self.BASE_URL, path.strip("/"))

    def _extract_csrf_token(self, _response: httpx.Response) -> str:
        """CSRFトークンをレスポンスから抽出する"""
        bs = BeautifulSoup(_response.text, "lxml")
        csrf_token_element = bs.find("meta", {"name": "csrf-token"})
        return (
            getattr(csrf_token_element, "get", lambda x, y: y)("content", "")
            if csrf_token_element
            else ""
        )

    def _extract_auth_params(self, _response: httpx.Response) -> dict:
        """認証パラメータをレスポンスから抽出する"""
        # gon.authorizationParamsからの情報抽出
        client_id_match = re.search(r'"clientId":"([^"]+)"', _response.text)
        client_id = client_id_match.group(0) if client_id_match else None
        redirect_uri_match = re.search(r'"redirectUri":"([^"]+)"', _response.text)
        redirect_uri = redirect_uri_match.group(1) if redirect_uri_match else None
        code_challenge_match = re.search(r'"codeChallenge":"([^"]+)"', _response.text)
        code_challenge = code_challenge_match.group(1) if code_challenge_match else None
        code_challenge_method_match = re.search(
            r'"codeChallengeMethod":"([^"]+)"', _response.text
        )
        code_challenge_method = (
            code_challenge_method_match.group(1)
            if code_challenge_method_match
            else None
        )
        response_type_match = re.search(r'"responseType":"([^"]+)"', _response.text)
        response_type = response_type_match.group(1) if response_type_match else None
        state_match = re.search(r'"state":"([^"]+)"', _response.text)
        state = state_match.group(1) if state_match else None
        nonce_match = re.search(r'"nonce":"([^"]+)"', _response.text)
        nonce = nonce_match.group(1) if nonce_match else None
        authenticity_token = self._extract_csrf_token(_response)
        return {
            "authenticity_token": authenticity_token,
            "_method": "post",
            "clientId": str(client_id).replace('"clientId":"', "").strip('"')
            if client_id
            else "",
            "redirectUri": redirect_uri if redirect_uri else "",
            "responseType": response_type if response_type else "",  # code
            "scope": "openid email profile address",
            "state": state if state else "",
            "codeChallenge": code_challenge if code_challenge else "",
            "codeChallengeMethod": code_challenge_method
            if code_challenge_method
            else "",
            "nonce": nonce if nonce else "",
            "selectAccount": True,
            "mfid_user[email]": self.email,
            "mfid_user[password]": self.password,
            "password-check": "on",
        }

    def _run_playwright(self, url: str, headless: bool = False):
        cookies = self.session.cookies
        if self.browser is None:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=headless)
            self.context = self.browser.new_context()

        # クッキーをPlaywrightに設定
        playwright_cookies = []
        for cookie in cookies.jar:
            expires = cookie.expires if cookie.expires is not None else -1
            playwright_cookies.append(
                {
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "expires": expires,
                    "secure": cookie.secure if cookie.secure is not None else False,
                }
            )
        self.context.add_cookies(playwright_cookies)  # type: ignore
        if self.page is None:
            if self.context is not None:
                self.page = self.context.new_page()
            else:
                raise ValueError("Browser context is not initialized.")
        if self.page is not None:
            self.page.goto(url)
            self.page.wait_for_url("https://moneyforward.com/")
        else:
            raise ValueError("Page is not initialized.")

    def login(self):
        sign_in_url = self.build_url("/sign_in")
        _response = self.session.get(
            sign_in_url, headers=self.headers, follow_redirects=True
        )
        _response.raise_for_status()
        params = self._extract_auth_params(_response)
        auth_url = "https://id.moneyforward.com/sign_in"
        headers = {
            **self.headers,
            "content-type": "application/x-www-form-urlencoded",
            "sec-ch-ua-platform": '"macOS"',
            "authority": "id.moneyforward.com",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "ja,en-US;q=0.9,en;q=0.8",
            "cache-control": "max-age=0",
            "origin": "https://id.moneyforward.com",
            "priority": "u=0, i",
            "referer": "https://id.moneyforward.com/sign_in/password?client_id={client_id}&code_challenge={code_challenge}&code_challenge_method={code_challenge_method}&nonce={nonce}&redirect_uri={redirect_uri}&response_type=code&scope=openid+email+profile+address&select_account=true&state={state}".format(
                client_id=params["clientId"],
                code_challenge=params["codeChallenge"],
                code_challenge_method=params["codeChallengeMethod"],
                nonce=params["nonce"],
                redirect_uri=params["redirectUri"],
                state=params["state"],
            ),
            "sec-ch-ua-mobile": "?0",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "upgrade-insecure-requests": "1",
        }
        _auth_response = self.session.post(
            auth_url, data=params, headers=headers, follow_redirects=True
        )
        _auth_response.raise_for_status()
        otp_url = _auth_response.url
        self._run_playwright(str(otp_url))

    def _navigate_to_last_month(self) -> None:
        """前月のデータに移動する処理を担当するヘルパー関数。"""
        if not isinstance(self.page, Page):
            raise ValueError("self.page is not Page object.")

        self.page.locator("span.fc-button-prev").click()
        start = time.time()
        calendar_header_locator = self.page.locator(
            "#in_out > div.date_range.transaction-in-out-header > span > h2"
        )

        # この特定のヘッダーのテキストが "Loading..." である間待機する
        while calendar_header_locator.text_content() == "Loading...":
            self.page.wait_for_timeout(99)
            if time.time() - start > 59:
                raise ValueError("Timeout waiting for calendar header to load.")

    def get_cf_data(self, is_last_month: bool = True) -> pd.DataFrame:
        """
        Playwrightを使用してCFデータページにアクセスする。
        既存のセッションからクッキーを取得し、ChromeブラウザでURLにアクセスする。

        Args:
            headless (bool): Headlessモードでブラウザを起動するかどうか。デフォルトはFalse（通常モード）。

        Returns:
            playwright.sync_api.Page: アクセスしたページオブジェクト。
        """
        if self.page is None or self.browser is None or self.context is None:
            self.login()
        if isinstance(self.page, Page):
            url = self.build_url("/cf")
            self.page.goto(url)
            if is_last_month:
                self._navigate_to_last_month()
            bs = BeautifulSoup(self.page.content(), "lxml")
            table_elm = bs.select_one("#cf-detail-table")
            dfs = pd.read_html(io.StringIO(str(table_elm)))
            return dfs[0]
        else:
            raise ValueError("self.page is not Page object.")

    def close(self):
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, "playwright"):
            self.playwright.stop()
