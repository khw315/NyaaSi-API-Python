"""
NyaaSi API - Python port of the Java NyaaSi-API library.

Entry points:
    NyaaSiApi.get_nyaa()     -> API for https://nyaa.si/
    NyaaSiApi.get_sukebei()  -> API for https://sukebei.nyaa.si/
"""

from .api import NyaaSiApi
from .auth_api import NyaaSiAuthApi
from .models import (
    SearchRequest,
    Filter,
    Sort,
    Ordering,
    TorrentPreview,
    TorrentInfo,
    DataSize,
    TorrentState,
    SubCategory,
    MainCategory,
    NyaaCategory,
    SukebeiCategory,
    Session,
)
from .exceptions import (
    NyaaSiException,
    HttpException,
    HttpErrorCodeException,
    WebScrapeException,
    LoginException,
    NoSuchTorrentException,
    NoSuchCommentException,
    IllegalCategoryException,
    PermissionException,
    CaptchaException,
    MissingTrackerException,
    CannotEditException,
)

__all__ = [
    "NyaaSiApi",
    "NyaaSiAuthApi",
    "SearchRequest",
    "Filter",
    "Sort",
    "Ordering",
    "TorrentPreview",
    "TorrentInfo",
    "DataSize",
    "TorrentState",
    "SubCategory",
    "MainCategory",
    "NyaaCategory",
    "SukebeiCategory",
    "Session",
    "NyaaSiException",
    "HttpException",
    "HttpErrorCodeException",
    "WebScrapeException",
    "LoginException",
    "NoSuchTorrentException",
    "NoSuchCommentException",
    "IllegalCategoryException",
    "PermissionException",
    "CaptchaException",
    "MissingTrackerException",
    "CannotEditException",
]
