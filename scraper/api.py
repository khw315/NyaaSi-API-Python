"""
Core (unauthenticated) NyaaSi API.
Mirrors NyaaSiApi / NyaaSiApiImpl from Java.
"""

from __future__ import annotations

import re
from typing import List, Optional, TYPE_CHECKING

import requests
from requests import Session as HttpSession

from .exceptions import (
    HttpException, HttpErrorCodeException, WebScrapeException,
    LoginException, NoSuchTorrentException, IllegalCategoryException,
)
from .models import (
    SearchRequest,
    TorrentInfo,
    Session,
    SearchResult
)
from . import parsers

if TYPE_CHECKING:
    from .auth_api import NyaaSiAuthApi


_DEFAULT_TIMEOUT = 30  # seconds


class NyaaSiApi:
    """
    Unauthenticated API for nyaa.si or sukebei.nyaa.si.

    Usage::

        nyaa    = NyaaSiApi.get_nyaa()
        sukebei = NyaaSiApi.get_sukebei()

        results = nyaa.search(SearchRequest().set_term("sword art online"))
        info    = nyaa.get_torrent_info(12345)
    """

    _nyaa_instance: Optional["NyaaSiApi"] = None
    _sukebei_instance: Optional["NyaaSiApi"] = None

    @classmethod
    def get_nyaa(cls) -> "NyaaSiApi":
        """Return the singleton API instance for https://nyaa.si/"""
        if cls._nyaa_instance is None:
            cls._nyaa_instance = cls(is_sukebei=False)
        return cls._nyaa_instance

    @classmethod
    def get_sukebei(cls) -> "NyaaSiApi":
        """Return the singleton API instance for https://sukebei.nyaa.si/"""
        if cls._sukebei_instance is None:
            cls._sukebei_instance = cls(is_sukebei=True)
        return cls._sukebei_instance

    # ------------------------------------------------------------------

    def __init__(self, is_sukebei: bool = False):
        self._is_sukebei = is_sukebei
        self._domain = "sukebei.nyaa.si" if is_sukebei else "nyaa.si"

    @property
    def is_sukebei(self) -> bool:
        return self._is_sukebei

    @property
    def base_url(self) -> str:
        return f"https://{self._domain}"

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, *, params: Optional[dict] = None,
             session: Optional[HttpSession] = None, cookies: Optional[dict] = None) -> requests.Response:
        try:
            requester = session or requests
            resp = requester.get(url, params=params, cookies=cookies,
                                 timeout=_DEFAULT_TIMEOUT, allow_redirects=False)
            return resp
        except requests.RequestException as exc:
            raise HttpException(f"GET {url} failed: {exc}") from exc

    def _post(self, url: str, *, data: Optional[dict] = None,
              files: Optional[dict] = None,
              session: Optional[HttpSession] = None,
              cookies: Optional[dict] = None) -> requests.Response:
        try:
            requester = session or requests
            resp = requester.post(url, data=data, files=files, cookies=cookies,
                                  timeout=_DEFAULT_TIMEOUT, allow_redirects=False)
            return resp
        except requests.RequestException as exc:
            raise HttpException(f"POST {url} failed: {exc}") from exc

    def _parse_page(self, html: str, parser_fn, *args):
        """Call a parser function, wrapping unexpected exceptions as WebScrapeException."""
        try:
            return parser_fn(html, *args)
        except (HttpException,) as exc:
            raise
        except Exception as exc:
            raise WebScrapeException(str(exc)) from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, request: SearchRequest) -> SearchResult:
        """
        Search for torrents.

        :param request: A :class:`SearchRequest` describing the query.
        :returns: A :class:`SearchResult` containing :class:`TorrentPreview` objects.
        :raises IllegalCategoryException: if a Sukebei category is used on Nyaa (or vice-versa).
        :raises WebScrapeException: if page parsing fails.
        :raises HttpException: on networking errors.
        """
        params: dict = {}

        if request.term is not None:
            params["q"] = request.term

        if request.category is not None:
            cat = request.category
            if cat.is_sukebei() != self._is_sukebei:
                raise IllegalCategoryException(
                    "Cannot use Sukebei categories on Nyaa (or vice-versa)"
                )
            params["c"] = f"{cat.get_main_category_id()}_{cat.get_sub_category_id()}"

        if request.filter is not None:
            params["f"] = str(request.filter.value)

        if request.user is not None:
            params["u"] = request.user

        if request.page is not None:
            params["p"] = str(request.page)

        if request.ordering is not None:
            params["o"] = request.ordering.value

        if request.sorted_by is not None:
            params["s"] = request.sorted_by.value

        resp = self._get(self.base_url, params=params)

        if resp.status_code == 404:
            return SearchResult()
        if resp.status_code == 200:
            results = self._parse_page(resp.text, parsers.parse_torrent_list, self._is_sukebei)
            return SearchResult(results)
        raise HttpErrorCodeException(resp.status_code)

    def get_torrent_info(self, torrent_id: int) -> TorrentInfo:
        """
        Fetch full details for a single torrent.

        :param torrent_id: Numeric ID of the torrent.
        :returns: :class:`TorrentInfo` object.
        :raises NoSuchTorrentException: if the torrent does not exist.
        :raises WebScrapeException: if page parsing fails.
        :raises HttpException: on networking errors.
        """
        resp = self._get(f"{self.base_url}/view/{torrent_id}")
        if resp.status_code == 404:
            raise NoSuchTorrentException(torrent_id)
        if resp.status_code != 200:
            raise HttpErrorCodeException(resp.status_code)
        return self._parse_page(resp.text, parsers.parse_torrent_info, self._is_sukebei)

    def login(self, username: str, password: str) -> "NyaaSiAuthApi":
        """
        Log in with username and password.

        :returns: An authenticated :class:`NyaaSiAuthApi` instance.
        :raises LoginException: if the credentials are wrong.
        :raises WebScrapeException: if page parsing fails.
        :raises HttpException: on networking errors.
        """
        # Lazy import to avoid circular dependency
        from .auth_api import NyaaSiAuthApi

        http_session = HttpSession()

        # Step 1 — Fetch the login page to get a CSRF token
        get_resp = self._get(f"{self.base_url}/login", session=http_session)
        csrf_token = self._parse_page(get_resp.text, parsers.parse_login_csrf_token)

        # Step 2 — POST credentials
        post_resp = self._post(
            f"{self.base_url}/login",
            data={
                "csrf_token": csrf_token,
                "username": username,
                "password": password,
            },
            session=http_session,
        )

        # A failed login redirects back to /login
        location = post_resp.headers.get("Location", "")
        if location.endswith("/login"):
            raise LoginException("Login failed — check username and password")

        # Extract the session cookie
        session_cookie = http_session.cookies.get("session")
        if not session_cookie:
            raise HttpException("Server did not respond with a session cookie")

        session = Session(session_id=session_cookie, is_sukebei=self._is_sukebei)
        return NyaaSiAuthApi(session=session, is_sukebei=self._is_sukebei)
