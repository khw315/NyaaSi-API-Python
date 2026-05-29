"""
NyaaSi API - Python port of the Java NyaaSi-API library.

Entry points:
    NyaaSiApi.get_nyaa()     -> API for https://nyaa.si/
    NyaaSiApi.get_sukebei()  -> API for https://sukebei.nyaa.si/
"""
import os
from .dns import setup_doh
from .api import NyaaSiApi
from .auth_api import NyaaSiAuthApi

# Auto-initialize DNS-over-HTTPS (DoH) engine if enabled
_DOH_ENABLED = os.environ.get("DOH_ENABLED", "true").lower() in ("true", "1", "yes")
_DOH_PROVIDER = os.environ.get("DOH_PROVIDER", "quad9").lower()

if _DOH_ENABLED:
    setup_doh(provider=_DOH_PROVIDER)

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
    "setup_doh",
]
