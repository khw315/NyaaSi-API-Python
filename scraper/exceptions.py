"""
Custom exception hierarchy for the NyaaSi Python API.
Mirrors the Java exception package de.kaysubs.tracker.nyaasi.exception.*
"""


class NyaaSiException(RuntimeError):
    """Base exception for all NyaaSi-specific errors."""


class HttpException(NyaaSiException):
    """Raised for generic networking / HTTP errors."""


class HttpErrorCodeException(HttpException):
    """Raised when the server returns an unexpected HTTP status code."""

    def __init__(self, status_code: int):
        super().__init__(f"Unexpected HTTP status code: {status_code}")
        self.status_code = status_code


class WebScrapeException(NyaaSiException):
    """Raised when HTML parsing / web-scraping fails."""


class LoginException(NyaaSiException):
    """Raised when login fails (wrong credentials)."""


class NoSuchTorrentException(NyaaSiException):
    """Raised when the requested torrent ID does not exist (404)."""

    def __init__(self, torrent_id: int):
        super().__init__(f"Torrent {torrent_id} not found")
        self.torrent_id = torrent_id


class NoSuchCommentException(NyaaSiException):
    """Raised when the requested comment does not exist (404)."""


class IllegalCategoryException(NyaaSiException):
    """Raised when a Sukebei category is used on Nyaa (or vice-versa)."""


class PermissionException(NyaaSiException):
    """Raised when the user lacks permission to perform an action (403)."""


class CaptchaException(NyaaSiException):
    """Raised when a CAPTCHA must be solved before the action is allowed."""


class MissingTrackerException(NyaaSiException):
    """Raised when the uploaded torrent doesn't contain the required tracker URL."""


class CannotEditException(NyaaSiException):
    """Raised when a comment can no longer be edited (edit window expired)."""
