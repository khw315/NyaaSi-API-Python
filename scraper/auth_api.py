"""
Authenticated NyaaSi API.
Mirrors NyaaSiAuthApi / NyaaSiAuthApiImpl from Java.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional

from requests import Session as HttpSession

from .api import NyaaSiApi
from .exceptions import (
    HttpErrorCodeException,
    WebScrapeException,
    LoginException,
    NoSuchTorrentException,
    NoSuchCommentException,
    PermissionException,
    IllegalCategoryException
)
from .models import (
    Session,
    SubCategory
)
from . import parsers


_VIEW_URL_RE = re.compile(r"https?://(?:sukebei\.)?nyaa\.si/view/([0-9]+)")


class EditTorrentRequest:
    """
    Holds the current state of a torrent's editable fields.
    Pass this to a callback given to :meth:`NyaaSiAuthApi.edit_torrent`.
    """

    def __init__(self, csrf_token: str, name: str, category: SubCategory,
                 information: str, description: str,
                 is_anonymous: bool, is_hidden: bool,
                 is_remake: bool, is_completed: bool):
        self.csrf_token = csrf_token
        self.name = name
        self.category = category
        self.information = information
        self.description = description
        self.is_anonymous = is_anonymous
        self.is_hidden = is_hidden
        self.is_remake = is_remake
        self.is_completed = is_completed


class UploadTorrentRequest:
    """Describes a torrent to be uploaded."""

    def __init__(self, seedfile: Path, name: str, category: SubCategory,
                 information: str = "", description: str = "",
                 is_anonymous: bool = False, is_hidden: bool = False,
                 is_remake: bool = False, is_completed: bool = False):
        self.seedfile = Path(seedfile)
        self.name = name
        self.category = category
        self.information = information
        self.description = description
        self.is_anonymous = is_anonymous
        self.is_hidden = is_hidden
        self.is_remake = is_remake
        self.is_completed = is_completed


class NyaaSiAuthApi(NyaaSiApi):
    """
    Authenticated API — exposes all unauthenticated methods plus actions
    that require a login (upload, delete, comment, …).

    Obtain an instance via :meth:`NyaaSiApi.login`.
    """

    def __init__(self, session: Session, is_sukebei: bool):
        super().__init__(is_sukebei=is_sukebei)
        self._session = session

    @property
    def session(self) -> Session:
        return self._session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cookie(self) -> dict:
        return self._session.to_cookie()

    def _authed_get(self, url: str, **kwargs) -> "requests.Response":
        return self._get(url, cookies=self._cookie(), **kwargs)

    def _authed_post(self, url: str, **kwargs) -> "requests.Response":
        return self._post(url, cookies=self._cookie(), **kwargs)

    def _fetch_account_info_page(self) -> str:
        resp = self._authed_get(f"{self.base_url}/profile")
        if resp.status_code != 200:
            raise HttpErrorCodeException(resp.status_code)
        return resp.text

    def _fetch_view_torrent_page(self, torrent_id: int) -> str:
        resp = self._authed_get(f"{self.base_url}/view/{torrent_id}")
        sc = resp.status_code
        if sc == 200:
            return resp.text
        if sc == 404:
            raise NoSuchTorrentException(torrent_id)
        raise HttpErrorCodeException(sc)

    def _get_edit_csrf_token(self, torrent_id: int) -> str:
        resp = self._authed_get(f"{self.base_url}/view/{torrent_id}/edit")
        sc = resp.status_code
        if sc == 200:
            return parsers.parse_delete_csrf_token(resp.text)
        if sc == 403:
            raise PermissionException()
        if sc == 404:
            raise NoSuchTorrentException(torrent_id)
        raise HttpErrorCodeException(sc)

    @staticmethod
    def _parse_view_url(url: str) -> int:
        m = _VIEW_URL_RE.search(url)
        if m:
            return int(m.group(1))
        raise WebScrapeException(f"Cannot parse view url: {url!r}")

    # ------------------------------------------------------------------
    # Account management
    # ------------------------------------------------------------------

    def get_account_info(self) -> dict:
        """
        Retrieve basic account information as a dict with keys:
        ``email``, ``username``, etc. (whatever the profile page exposes).
        """
        html = self._fetch_account_info_page()
        return parsers.parse_account_info_html(html)

    def change_email(self, current_password: str, new_email: str) -> None:
        """Change the account's email address."""
        tokens = parsers.parse_account_info_html(self._fetch_account_info_page())
        csrf_token = tokens.get("email_token", "")

        self._authed_post(
            f"{self.base_url}/profile",
            data={
                "csrf_token": csrf_token,
                "email": new_email,
                "current_password": current_password,
            },
        )

    def change_password(self, current_password: str, new_password: str) -> None:
        """Change the account's password."""
        if not current_password:
            raise LoginException("Current password must not be empty")

        tokens = parsers.parse_account_info_html(self._fetch_account_info_page())
        csrf_token = tokens.get("password_token", "")

        resp = self._authed_post(
            f"{self.base_url}/profile",
            data={
                "csrf_token": csrf_token,
                "current_password": current_password,
                "new_password": new_password,
                "password_confirm": new_password,
            },
        )
        sc = resp.status_code
        if sc not in (200, 302):
            raise HttpErrorCodeException(sc)

    # ------------------------------------------------------------------
    # Torrent management
    # ------------------------------------------------------------------

    def upload_torrent(self, request: UploadTorrentRequest) -> int:
        """
        Upload a torrent file.

        :param request: :class:`UploadTorrentRequest` with all upload parameters.
        :returns: The ID of the newly created torrent.
        :raises IllegalCategoryException: wrong category for this site.
        """
        if request.category.is_sukebei() != self._is_sukebei:
            raise IllegalCategoryException()

        # Fetch CSRF token from the upload page
        token_resp = self._authed_get(f"{self.base_url}/upload")
        csrf_token = parsers.parse_upload_csrf_token(token_resp.text)

        cat = request.category
        category_str = f"{cat.get_main_category_id()}_{cat.get_sub_category_id()}"

        data = {
            "csrf_token": csrf_token,
            "display_name": request.name,
            "category": category_str,
            "information": request.information,
            "description": request.description,
        }
        if request.is_anonymous:
            data["is_anonymous"] = "y"
        if request.is_hidden:
            data["is_hidden"] = "y"
        if request.is_remake:
            data["is_remake"] = "y"
        if request.is_completed:
            data["is_complete"] = "y"

        with open(request.seedfile, "rb") as fh:
            files = {
                "torrent_file": (
                    request.seedfile.name,
                    fh,
                    "application/x-bittorrent",
                )
            }
            resp = self._authed_post(f"{self.base_url}/upload", data=data, files=files)

        location = resp.headers.get("Location", "")
        return self._parse_view_url(location)

    def delete_torrent(self, torrent_id: int) -> None:
        """
        Delete a torrent you own.

        :raises PermissionException: you do not own this torrent.
        :raises NoSuchTorrentException: torrent not found.
        """
        csrf_token = self._get_edit_csrf_token(torrent_id)
        self._authed_post(
            f"{self.base_url}/view/{torrent_id}/edit",
            data={"csrf_token": csrf_token, "delete": "Delete"},
        )

    def edit_torrent(self, torrent_id: int,
                     callback: Callable[[EditTorrentRequest], None]) -> None:
        """
        Edit a torrent you own.

        :param torrent_id: ID of the torrent to edit.
        :param callback: A function that receives an :class:`EditTorrentRequest`
                         and modifies its fields in-place.
        :raises IllegalCategoryException: cross-site category mismatch.
        :raises PermissionException: you do not own this torrent.
        :raises NoSuchTorrentException: torrent not found.
        """
        request = self._get_edit_request(torrent_id)
        callback(request)

        if request.category.is_sukebei() != self._is_sukebei:
            raise IllegalCategoryException()

        cat = request.category
        data = {
            "csrf_token": request.csrf_token,
            "display_name": request.name,
            "category": f"{cat.get_main_category_id()}_{cat.get_sub_category_id()}",
            "information": request.information,
            "description": request.description,
            "submit": "Save Changes",
        }
        if request.is_anonymous:
            data["is_anonymous"] = "y"
        if request.is_hidden:
            data["is_hidden"] = "y"
        if request.is_remake:
            data["is_remake"] = "y"
        if request.is_completed:
            data["is_complete"] = "y"

        self._authed_post(f"{self.base_url}/view/{torrent_id}/edit", data=data)

    def _get_edit_request(self, torrent_id: int) -> EditTorrentRequest:
        resp = self._authed_get(f"{self.base_url}/view/{torrent_id}/edit")
        sc = resp.status_code
        if sc == 403:
            raise PermissionException()
        if sc == 404:
            raise NoSuchTorrentException(torrent_id)
        if sc != 200:
            raise HttpErrorCodeException(sc)
        # Parse the edit page to populate an EditTorrentRequest
        return _parse_edit_page(resp.text, self._is_sukebei)

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def write_comment(self, torrent_id: int, message: str) -> int:
        """
        Post a comment on a torrent.

        :returns: The ID of the newly posted comment.
        :raises NoSuchTorrentException: torrent not found.
        """
        view_html = self._fetch_view_torrent_page(torrent_id)
        csrf_token = parsers.get_csrf_token(
            __import__("bs4", fromlist=["BeautifulSoup"]).BeautifulSoup(view_html, "html.parser")
        )

        resp = self._authed_post(
            f"{self.base_url}/view/{torrent_id}",
            data={"csrf_token": csrf_token, "comment": message},
        )
        if resp.status_code == 302:
            redirect_url = resp.headers.get("Location", "")
            # The fragment contains the comment anchor e.g. #c12345
            anchor = redirect_url.rsplit("#", 1)[-1]
            m = re.match(r"c([0-9]+)", anchor)
            return int(m.group(1)) if m else 0
        raise HttpErrorCodeException(resp.status_code)

    def edit_comment(self, torrent_id: int, comment_id: int, new_message: str) -> None:
        """
        Edit one of your comments (only within the first hour after posting).

        :raises NoSuchTorrentException: torrent not found.
        :raises NoSuchCommentException: comment not found.
        :raises CannotEditException: edit window has passed.
        """
        view_html = self._fetch_view_torrent_page(torrent_id)
        # Find the CSRF token for *this* comment's edit form
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(view_html, "html.parser")
        comment_div = soup.find("div", {"id": f"torrent-comment{comment_id}"})
        if not comment_div:
            raise NoSuchCommentException()

        csrf_token = parsers.get_csrf_token(soup)

        resp = self._authed_post(
            f"{self.base_url}/view/{torrent_id}/comment/{comment_id}/edit",
            data={"csrf_token": csrf_token, "comment": new_message},
        )
        sc = resp.status_code
        if sc == 200:
            return
        from .exceptions import CannotEditException
        if sc == 400:
            raise CannotEditException()
        raise HttpErrorCodeException(sc)

    def delete_comment(self, torrent_id: int, comment_id: int) -> None:
        """
        Delete one of your comments.

        :raises NoSuchCommentException: comment not found.
        :raises PermissionException: comment belongs to another user.
        """
        resp = self._authed_post(
            f"{self.base_url}/view/{torrent_id}/comment/{comment_id}/delete",
            data={"submit": ""},
        )
        sc = resp.status_code
        if sc == 302:
            return
        if sc == 403:
            raise PermissionException()
        if sc == 404:
            raise NoSuchCommentException()
        raise HttpErrorCodeException(sc)


# ---------------------------------------------------------------------------
# Helper: parse the edit-torrent form
# ---------------------------------------------------------------------------

def _parse_edit_page(html: str, is_sukebei: bool) -> EditTorrentRequest:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    csrf_token = parsers.get_csrf_token(soup)

    form = soup.select_one("form[method=POST]")

    def _val(name: str) -> str:
        tag = form.select_one(f"input[name={name}], textarea[name={name}]")
        return tag.get("value", tag.get_text()) if tag else ""

    def _checked(name: str) -> bool:
        tag = form.select_one(f"input[name={name}]")
        return tag is not None and tag.has_attr("checked")

    name = _val("display_name")
    information = _val("information")
    description = form.select_one("textarea[name=description]")
    desc_text = description.get_text() if description else ""

    cat_select = form.select_one("select[name=category]")
    cat_str = ""
    if cat_select:
        selected = cat_select.select_one("option[selected]")
        if selected:
            cat_str = selected.get("value", "")

    category = parsers.parse_sub_category(cat_str, is_url=False, is_sukebei=is_sukebei) if cat_str else None

    return EditTorrentRequest(
        csrf_token=csrf_token,
        name=name,
        category=category,
        information=information,
        description=desc_text,
        is_anonymous=_checked("is_anonymous"),
        is_hidden=_checked("is_hidden"),
        is_remake=_checked("is_remake"),
        is_completed=_checked("is_complete"),
    )
