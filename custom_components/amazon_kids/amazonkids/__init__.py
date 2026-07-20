"""Unofficial async client for the Amazon Kids Parent Dashboard."""

from .client import (
    AmazonKidsAuthError,
    AmazonKidsClient,
    AmazonKidsError,
    RESUME_VALUE,
)

__all__ = [
    "AmazonKidsClient",
    "AmazonKidsError",
    "AmazonKidsAuthError",
    "RESUME_VALUE",
]

__version__ = "0.2.2"
