"""
HTML parsing utilities for the NyaaSi API.
Mirrors de.kaysubs.tracker.nyaasi.webscrape.ParseUtils (and the various Parser classes).
Uses BeautifulSoup4 instead of jsoup.
"""

from __future__ import annotations

import datetime
import re

from bs4 import BeautifulSoup, Tag

from .exceptions import WebScrapeException
from .models import (
    DataSize,
    DataUnit,
    SubCategory,
    TorrentState,
    TorrentPreview,
    TorrentInfo,
    TorrentComment,
    TorrentFile,
    TorrentFolder,
    FileNode,
    NyaaCategory,
    SukebeiCategory
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_data_unit(name: str) -> DataUnit:
    try:
        return DataUnit.from_name(name)
    except ValueError:
        raise WebScrapeException(f'Unknown data unit: "{name}"')


def parse_data_size(text: str) -> DataSize:
    """Parse e.g. '1.2 GiB' -> DataSize(1.2, DataUnit.GIGABYTE)"""
    parts = text.strip().split()
    if len(parts) != 2:
        raise WebScrapeException(f"Cannot parse data size: {text!r}")

    unit = _parse_data_unit(parts[1])
    size = float(parts[0])

    return DataSize(size, unit)


def parse_timestamp(ts: str) -> datetime.datetime:
    """Convert a Unix-epoch string to a UTC datetime."""
    return datetime.datetime.utcfromtimestamp(int(ts))


_CATEGORY_URL_RE = re.compile(r"/\?c=([0-9])_([0-9])")
_CATEGORY_ID_RE = re.compile(r"([0-9])_([0-9])")


def parse_sub_category(value: str, is_url: bool, is_sukebei: bool) -> SubCategory:
    """Parse a category value from either a URL fragment or a raw 'X_Y' string."""
    pattern = _CATEGORY_URL_RE if is_url else _CATEGORY_ID_RE
    m = pattern.match(value)
    if not m:
        raise WebScrapeException(f"Cannot parse category: {value!r}")

    main_id = int(m.group(1))
    sub_id = int(m.group(2))

    main_cat = (SukebeiCategory.from_id(main_id) if is_sukebei
                else NyaaCategory.from_id(main_id))
    return main_cat.get_subcategory_from_id(sub_id)


def get_csrf_token(soup: Tag) -> str:
    """Extract the CSRF token from a POST form on the page."""
    token = soup.select_one("form[method=POST] input#csrf_token")
    if token and token.get("value"):
        return token["value"]
    raise WebScrapeException("Cannot extract CSRF token")


# ---------------------------------------------------------------------------
# Torrent-list page parser
# ---------------------------------------------------------------------------

_VIEW_URL_RE = re.compile(r"/view/([0-9]+)")


def _parse_view_url(href: str) -> int:
    m = _VIEW_URL_RE.search(href)
    if m:
        return int(m.group(1))
    raise WebScrapeException(f"Cannot parse view url: {href!r}")


def parse_torrent_list(html: str, is_sukebei: bool) -> list[TorrentPreview]:
    """Parse the main search-result listing page into TorrentPreview objects."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.torrent-list > tbody")
    if table is None:
        raise WebScrapeException("Cannot find torrent-list table")

    results = []
    for row in table.find_all("tr"):
        results.append(_parse_torrent_row(row, is_sukebei))
    return results


def _parse_torrent_row(row: Tag, is_sukebei: bool) -> TorrentPreview:
    if "danger" in row.get("class", []):
        state = TorrentState.REMAKE
    elif "success" in row.get("class", []):
        state = TorrentState.TRUSTED
    else:
        state = TorrentState.NORMAL

    cells = row.find_all("td")

    category = parse_sub_category(
        cells[0].select_one("a")["href"], is_url=True, is_sukebei=is_sukebei
    )

    title_cell = cells[1]
    title_link = title_cell.select_one("a:not(.comments)")
    title = title_link.get_text(strip=True)
    torrent_id = _parse_view_url(title_link["href"])

    comment_tag = title_cell.select_one("a.comments")
    comment_count = int(comment_tag.get_text(strip=True)) if comment_tag else 0

    links = cells[2].find_all("a")
    base = "https://sukebei.nyaa.si" if is_sukebei else "https://nyaa.si"
    download_href = links[0]["href"]
    download_link = download_href if download_href.startswith("http") else base + download_href
    magnet_link = links[1]["href"]

    size = parse_data_size(cells[3].get_text(strip=True))
    date = parse_timestamp(cells[4]["data-timestamp"])
    seeders = int(cells[5].get_text(strip=True))
    leechers = int(cells[6].get_text(strip=True))
    completed = int(cells[7].get_text(strip=True))

    return TorrentPreview(
        id=torrent_id,
        torrent_state=state,
        category=category,
        title=title,
        comment_count=comment_count,
        download_link=download_link,
        magnet_link=magnet_link,
        size=size,
        date=date,
        seeders=seeders,
        leechers=leechers,
        completed=completed,
    )


# ---------------------------------------------------------------------------
# Torrent-info page parser
# ---------------------------------------------------------------------------

_COMMENT_DIV_RE = re.compile(r"torrent-comment([0-9]+)")


def parse_torrent_info(html: str, is_sukebei: bool) -> TorrentInfo:
    soup = BeautifulSoup(html, "html.parser")
    info = TorrentInfo()
    _parse_main_panel(soup, info, is_sukebei)
    _parse_file_list(soup, info)
    _parse_description(soup, info)
    _parse_comments(soup, info)
    return info


def _parse_main_panel(soup: BeautifulSoup, info: TorrentInfo, is_sukebei: bool):
    # Find the panel that has a footer
    panel = None
    for div in soup.select("div.panel"):
        if div.select_one("div.panel-footer.clearfix"):
            panel = div
            break
    if panel is None:
        raise WebScrapeException("Cannot find main panel")

    classes = panel.get("class", [])
    if "panel-danger" in classes:
        info.torrent_state = TorrentState.REMAKE
    elif "panel-success" in classes:
        info.torrent_state = TorrentState.TRUSTED
    else:
        info.torrent_state = TorrentState.NORMAL

    info.title = panel.select_one("div.panel-heading .panel-title").get_text(strip=True)

    body = panel.select_one("div.panel-body")
    rows = body.select("div.row")

    def get_cell(row_idx: int, col_idx: int) -> Tag:
        return rows[row_idx].select("div.col-md-5")[col_idx]

    # Row 0, col 0: category (second <a> link inside)
    cat_links = get_cell(0, 0).select("a")
    info.category = parse_sub_category(cat_links[1]["href"], is_url=True, is_sukebei=is_sukebei)

    # Row 1, col 0: uploader
    uploader_tag = get_cell(1, 0).select_one("a")
    info.uploader = uploader_tag.get_text(strip=True) if uploader_tag else None

    # Row 2, col 0: information
    info.information = get_cell(2, 0).get_text(strip=True)

    # Row 3, col 0: size
    info.size = parse_data_size(get_cell(3, 0).get_text(strip=True))

    # Row 0, col 1: date
    info.date = parse_timestamp(get_cell(0, 1)["data-timestamp"])

    # Row 1, col 1: seeders
    info.seeders = int(get_cell(1, 1).select_one("span").get_text(strip=True))

    # Row 2, col 1: leechers
    info.leechers = int(get_cell(2, 1).select_one("span").get_text(strip=True))

    # Row 3, col 1: completed
    info.completed = int(get_cell(3, 1).get_text(strip=True))

    # Row 4, col 0: hash
    info.hash = get_cell(4, 0).select_one("kbd").get_text(strip=True)

    footer = panel.select_one("div.panel-footer.clearfix")
    dl_href = footer.select_one("a[href^=/download/]")["href"]
    base = "https://sukebei.nyaa.si" if is_sukebei else "https://nyaa.si"
    info.download_link = base + dl_href if not dl_href.startswith("http") else dl_href
    info.magnet_link = footer.select_one("a.card-footer-item")["href"]


def _parse_file_list(soup: BeautifulSoup, info: TorrentInfo):
    root_li = soup.select_one("div.torrent-file-list > ul > li")
    if root_li:
        info.file = _parse_file_node(root_li)


def _parse_file_node(li: Tag) -> FileNode:
    folder_link = li.select_one("a.folder")
    if folder_link is None:
        # It's a file
        name = next(li.strings, "").strip()
        size_span = li.select_one("span.file-size")
        size_text = size_span.get_text(strip=True)
        # Strip surrounding brackets e.g. "(1.2 GiB)"
        size_text = size_text.strip("()")
        return TorrentFile(name=name, size=parse_data_size(size_text))
    else:
        name = folder_link.get_text(strip=True)
        ul = li.select_one("ul")
        children = []
        if ul:
            for child_li in ul.find_all("li", recursive=False):
                children.append(_parse_file_node(child_li))
        return TorrentFolder(name=name, children=children)


def _parse_description(soup: BeautifulSoup, info: TorrentInfo):
    desc_div = soup.select_one("div#torrent-description")
    info.description = desc_div.get_text() if desc_div else ""


def _parse_comments(soup: BeautifulSoup, info: TorrentInfo):
    comments_div = soup.select_one("div#comments")
    if not comments_div:
        return

    for panel in comments_div.select("div.comment-panel"):
        info.comments.append(_parse_comment(panel))


def _parse_comment(panel: Tag) -> TorrentComment:
    user_link = panel.select_one("a[href^=/user/]")
    username = user_link.get_text(strip=True)
    is_trusted = user_link.get("title", "") == "Trusted"

    avatar_tag = panel.select_one("img.avatar")
    avatar = avatar_tag["src"] if avatar_tag else ""

    ts_tag = panel.select_one("small[data-timestamp]")
    date = parse_timestamp(ts_tag["data-timestamp"])

    content_div = panel.select_one("div.comment-content")
    m = _COMMENT_DIV_RE.match(content_div.get("id", ""))
    comment_id = int(m.group(1)) if m else 0

    return TorrentComment(
        comment_id=comment_id,
        username=username,
        is_trusted=is_trusted,
        avatar=avatar,
        date=date,
        text=content_div.get_text(),
    )


# ---------------------------------------------------------------------------
# Login-page parsers
# ---------------------------------------------------------------------------

def parse_login_csrf_token(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return get_csrf_token(soup)


def parse_upload_csrf_token(html: str) -> str:
    return parse_login_csrf_token(html)


def parse_delete_csrf_token(html: str) -> str:
    return parse_login_csrf_token(html)


def parse_account_info_html(html: str) -> dict:
    """Return a dict with keys: email_token, password_token."""
    soup = BeautifulSoup(html, "html.parser")
    forms = soup.select("form[method=POST]")
    tokens = {}
    for form in forms:
        token_input = form.select_one("input#csrf_token")
        if not token_input:
            continue
        if form.select_one("input[name=email]"):
            tokens["email_token"] = token_input.get("value", "")
        elif form.select_one("input[name=new_password]"):
            tokens["password_token"] = token_input.get("value", "")
    return tokens
