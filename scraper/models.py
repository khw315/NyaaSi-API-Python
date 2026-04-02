"""
Data models for the NyaaSi Python API.

Mirrors the de.kaysubs.tracker.nyaasi.model.* package.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Iterable

class SearchResult(list):
    """List of TorrentPreview items with a helper to output JSON/dict data."""
    
    def __init__(self, iterable: Iterable = ()):
        super().__init__(iterable)
        
    def to_dict(self) -> dict:
        return {
            "count": len(self),
            "data": [item.to_dict() for item in self]
        }


# ---------------------------------------------------------------------------
# DataSize
# ---------------------------------------------------------------------------

class DataUnit(Enum):
    BYTE = "Bytes"
    KILOBYTE = "KiB"
    MEGABYTE = "MiB"
    GIGABYTE = "GiB"
    TERABYTE = "TiB"

    @classmethod
    def from_name(cls, name: str) -> "DataUnit":
        for member in cls:
            if member.value.lower() == name.lower():
                return member
        raise ValueError(f'Unknown data unit: "{name}"')

    # Ordered list used when downscaling fractional values
    _order_: str  # populated below


# Build a simple ordered list so we can navigate up/down the units
_UNIT_ORDER = [DataUnit.BYTE, DataUnit.KILOBYTE, DataUnit.MEGABYTE,
               DataUnit.GIGABYTE, DataUnit.TERABYTE]


@dataclass(frozen=True)
class DataSize:
    value: float
    unit: DataUnit

    def __str__(self) -> str:
        # Format as int if it's a whole number, otherwise show one decimal place
        if self.value == int(self.value):
            return f"{int(self.value)} {self.unit.value}"
        return f"{self.value:.1f} {self.unit.value}"

    def to_bytes(self) -> int:
        idx = _UNIT_ORDER.index(self.unit)
        return self.value * (1024 ** idx)


# ---------------------------------------------------------------------------
# TorrentState
# ---------------------------------------------------------------------------

class TorrentState(Enum):
    NORMAL = "normal"
    REMAKE = "remake"
    TRUSTED = "trusted"


# ---------------------------------------------------------------------------
# Category hierarchy (Nyaa + Sukebei)
# ---------------------------------------------------------------------------

class Category:
    """Marker base class shared by MainCategory and SubCategory."""

    def is_sukebei(self) -> bool:
        raise NotImplementedError

    def get_main_category_id(self) -> int:
        raise NotImplementedError

    def get_sub_category_id(self) -> int:
        raise NotImplementedError


class SubCategory(Category):
    def __init__(self, main_category: "MainCategory", name: str, sub_id: int):
        self._main = main_category
        self._name = name
        self._sub_id = sub_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def main_category(self) -> "MainCategory":
        return self._main

    def is_sukebei(self) -> bool:
        return self._main.is_sukebei()

    def get_main_category_id(self) -> int:
        return self._main.get_main_category_id()

    def get_sub_category_id(self) -> int:
        return self._sub_id

    def __repr__(self) -> str:
        return (f"SubCategory(name={self._name!r}, "
                f"main={self.get_main_category_id()}, sub={self._sub_id})")


class MainCategory(Category):
    def __init__(self, main_id: int, name: str = ""):
        self._main_id = main_id
        self._name = name
        self._sub_categories: Optional[List[SubCategory]] = None

    @property
    def name(self) -> str:
        return self._name

    def is_sukebei(self) -> bool:
        raise NotImplementedError

    def get_main_category_id(self) -> int:
        return self._main_id

    def get_sub_category_id(self) -> int:
        return 0

    def get_sub_categories(self) -> List[SubCategory]:
        """Return all SubCategory attributes defined on this instance."""
        if self._sub_categories is None:
            self._sub_categories = [
                v for v in self.__dict__.values()
                if isinstance(v, SubCategory)
            ]
        return self._sub_categories

    def get_subcategory_from_id(self, sub_id: int) -> SubCategory:
        for sc in self.get_sub_categories():
            if sc.get_sub_category_id() == sub_id:
                return sc
        raise ValueError(f"Category {self!r} has no sub-category with id {sub_id}")


# ---------------------------------------------------------------------------
# Nyaa categories
# ---------------------------------------------------------------------------

class _NyaaAnime(MainCategory):
    def __init__(self):
        super().__init__(1, "Anime")
        self.AMV = SubCategory(self, "Anime Music Video", 1)
        self.ENGLISH = SubCategory(self, "English-translated", 2)
        self.NON_ENGLISH = SubCategory(self, "Non-English-translated", 3)
        self.RAW = SubCategory(self, "Raw", 4)

    def is_sukebei(self) -> bool:
        return False


class _NyaaAudio(MainCategory):
    def __init__(self):
        super().__init__(2, "Audio")
        self.LOSSLESS = SubCategory(self, "Lossless", 1)
        self.LOSSY = SubCategory(self, "Lossy", 2)

    def is_sukebei(self) -> bool:
        return False


class _NyaaLiterature(MainCategory):
    def __init__(self):
        super().__init__(3, "Literature")
        self.ENGLISH = SubCategory(self, "English-translated", 1)
        self.NON_ENGLISH = SubCategory(self, "Non-English-translated", 2)
        self.RAW = SubCategory(self, "Raw", 3)

    def is_sukebei(self) -> bool:
        return False


class _NyaaLiveAction(MainCategory):
    def __init__(self):
        super().__init__(4, "Live Action")
        self.ENGLISH = SubCategory(self, "English-translated", 1)
        self.IDOL_PV = SubCategory(self, "Idol/Promotional Video", 2)
        self.NON_ENGLISH = SubCategory(self, "Non-English-translated", 3)
        self.RAW = SubCategory(self, "Raw", 4)

    def is_sukebei(self) -> bool:
        return False


class _NyaaPictures(MainCategory):
    def __init__(self):
        super().__init__(5, "Pictures")
        self.GRAPHICS = SubCategory(self, "Graphics", 1)
        self.PHOTOS = SubCategory(self, "Photos", 2)

    def is_sukebei(self) -> bool:
        return False


class _NyaaSoftware(MainCategory):
    def __init__(self):
        super().__init__(6, "Software")
        self.APPLICATIONS = SubCategory(self, "Applications", 1)
        self.GAMES = SubCategory(self, "Games", 2)

    def is_sukebei(self) -> bool:
        return False


class NyaaCategory:
    """Nyaa.si category constants, analogous to NyaaCategory enum in Java."""
    ANIME = _NyaaAnime()
    AUDIO = _NyaaAudio()
    LITERATURE = _NyaaLiterature()
    LIVE_ACTION = _NyaaLiveAction()
    PICTURES = _NyaaPictures()
    SOFTWARE = _NyaaSoftware()

    _CATEGORIES = [ANIME, AUDIO, LITERATURE, LIVE_ACTION, PICTURES, SOFTWARE]

    @classmethod
    def from_id(cls, main_id: int) -> MainCategory:
        for cat in cls._CATEGORIES:
            if cat.get_main_category_id() == main_id:
                return cat
        raise ValueError(f"Unknown Nyaa main category id: {main_id}")


# ---------------------------------------------------------------------------
# Sukebei categories
# ---------------------------------------------------------------------------

class _SukebeiArt(MainCategory):
    def __init__(self):
        super().__init__(1, "Art")
        self.ANIME = SubCategory(self, "Anime", 1)
        self.DOUJINSHI = SubCategory(self, "Doujinshi", 2)
        self.GAMES = SubCategory(self, "Games", 3)
        self.MANGA = SubCategory(self, "Manga", 4)
        self.PICTURES = SubCategory(self, "Pictures", 5)

    def is_sukebei(self) -> bool:
        return True


class _SukebeiRealLife(MainCategory):
    def __init__(self):
        super().__init__(2, "Real Life")
        self.PHOTOBOOKS = SubCategory(self, "Photobooks and Pictures", 1)
        self.VIDEOS = SubCategory(self, "Videos", 2)

    def is_sukebei(self) -> bool:
        return True


class SukebeiCategory:
    """Sukebei.nyaa.si category constants."""
    ART = _SukebeiArt()
    REAL_LIFE = _SukebeiRealLife()

    _CATEGORIES = [ART, REAL_LIFE]

    @classmethod
    def from_id(cls, main_id: int) -> MainCategory:
        for cat in cls._CATEGORIES:
            if cat.get_main_category_id() == main_id:
                return cat
        raise ValueError(f"Unknown Sukebei main category id: {main_id}")


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

@dataclass
class Session:
    session_id: str
    is_sukebei: bool

    def to_cookie(self) -> dict:
        """Return a requests-compatible cookie dict."""
        return {"session": self.session_id}

    @property
    def domain(self) -> str:
        return "sukebei.nyaa.si" if self.is_sukebei else "nyaa.si"


# ---------------------------------------------------------------------------
# SearchRequest
# ---------------------------------------------------------------------------

class Filter(Enum):
    NONE = 0
    NO_REMAKES = 1
    TRUSTED_ONLY = 2


class Ordering(Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"


class Sort(Enum):
    COMMENTS = "comments"
    SIZE = "size"
    DATE = "id"
    SEEDERS = "seeders"
    LEECHERS = "leechers"
    DOWNLOADS = "downloads"


class SearchRequest:
    """
    Builder-style search request.

    Example::

        req = (SearchRequest()
               .set_term("sword art online")
               .set_filter(Filter.TRUSTED_ONLY)
               .set_page(1))
    """

    def __init__(self):
        self.term: Optional[str] = None
        self.category: Optional[SubCategory] = None
        self.filter: Optional[Filter] = None
        self.user: Optional[str] = None
        self.page: Optional[int] = None
        self.ordering: Optional[Ordering] = None
        self.sorted_by: Optional[Sort] = None

    def set_term(self, term: Optional[str]) -> "SearchRequest":
        self.term = term
        return self

    def set_category(self, category: Optional[Category]) -> "SearchRequest":
        self.category = category
        return self

    def set_filter(self, f: Optional[Filter]) -> "SearchRequest":
        self.filter = f
        return self

    def set_user(self, user: Optional[str]) -> "SearchRequest":
        self.user = user
        return self

    def set_page(self, page: Optional[int]) -> "SearchRequest":
        self.page = page
        return self

    def set_ordering(self, ordering: Optional[Ordering]) -> "SearchRequest":
        self.ordering = ordering
        return self

    def set_sorted_by(self, sort: Optional[Sort]) -> "SearchRequest":
        self.sorted_by = sort
        return self


# ---------------------------------------------------------------------------
# TorrentPreview
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TorrentPreview:
    id: int
    torrent_state: TorrentState
    category: SubCategory
    title: str
    comment_count: int
    download_link: str
    magnet_link: str
    size: DataSize
    date: datetime.datetime
    seeders: int
    leechers: int
    completed: int

    def __repr__(self) -> str:
        return (f"TorrentPreview(id={self.id}, title={self.title!r}, "
                f"seeders={self.seeders}, leechers={self.leechers})")

    def to_dict(self) -> dict:
        cat_name = self.category.name
        if self.category.main_category.name:
            cat_name = f"{self.category.main_category.name} - {cat_name}"

        domain = "sukebei.nyaa.si" if self.category.is_sukebei() else "nyaa.si"
        link = f"https://{domain}/view/{self.id}"

        return {
            "category": cat_name,
            "title": self.title,
            "link": link,
            "torrent": self.download_link,
            "magnet": self.magnet_link,
            "size": str(self.size),
            "time": self.date.strftime("%Y-%m-%d %H:%M"),
            "seeders": self.seeders,
            "leechers": self.leechers,
            "downloads": self.completed
        }


# ---------------------------------------------------------------------------
# TorrentInfo
# ---------------------------------------------------------------------------

@dataclass
class TorrentComment:
    comment_id: int
    username: str
    is_trusted: bool
    avatar: str
    date: datetime.datetime
    text: str  # plain text of the comment


class FileNode:
    """Abstract base for file-tree nodes."""
    name: str


@dataclass
class TorrentFile(FileNode):
    name: str
    size: DataSize


@dataclass
class TorrentFolder(FileNode):
    name: str
    children: List[FileNode]


@dataclass
class TorrentInfo:
    title: str = ""
    description: str = ""
    category: Optional[SubCategory] = None
    size: Optional[DataSize] = None
    date: Optional[datetime.datetime] = None
    uploader: Optional[str] = None
    torrent_state: TorrentState = TorrentState.NORMAL
    seeders: int = 0
    leechers: int = 0
    completed: int = 0
    information: str = ""
    hash: str = ""
    download_link: str = ""
    magnet_link: str = ""
    file: Optional[FileNode] = None
    comments: List[TorrentComment] = field(default_factory=list)

    def __repr__(self) -> str:
        return (f"TorrentInfo(title={self.title!r}, seeders={self.seeders}, "
                f"leechers={self.leechers}, hash={self.hash!r})")

    def to_dict(self) -> dict:
        cat_name = self.category.name if self.category else ""
        if self.category and self.category.main_category.name:
            cat_name = f"{self.category.main_category.name} - {cat_name}"

        return {
            "title": self.title,
            "description": self.description,
            "category": cat_name,
            "size": str(self.size) if self.size else "",
            "date": self.date.strftime("%Y-%m-%d %H:%M:%S") if self.date else "",
            "uploader": self.uploader,
            "seeders": self.seeders,
            "leechers": self.leechers,
            "completed": self.completed,
            "information": self.information,
            "hash": self.hash,
            "download_link": self.download_link,
            "magnet_link": self.magnet_link,
            "comments": [
                {
                    "user": c.username,
                    "date": c.date.strftime("%Y-%m-%d %H:%M:%S") if c.date else "",
                    "text": c.text,
                }
                for c in self.comments
            ]
        }
