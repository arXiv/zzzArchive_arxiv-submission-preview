"""Core concepts for the submission preview service."""

from typing import NamedTuple, Optional, IO
from datetime import datetime


class Preview(NamedTuple):
    """A submission preview."""

    source_id: str
    """Unique identifier for the source package in the file manager service."""

    checksum: str
    """URL-safe base64-encoded MD5 hash of the source package."""

    added: datetime
    """Datetime when the preview was added."""

    content: Optional['Content'] = None
    """The preview content, if available."""


class Content(NamedTuple):
    """Content of the submission preview."""

    stream: IO[bytes]
    """
    An IO object, the ``read()`` method of which returns bytes.

    For example, a filepointer opened with ``rb``.
    """

    content_type: str = 'application/json'
    """Content type of the preview."""
