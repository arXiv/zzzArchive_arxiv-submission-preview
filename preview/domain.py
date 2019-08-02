"""Core concepts for the submission preview service."""

from typing import NamedTuple, Optional, IO
from datetime import datetime

PDF = 'application/pdf'


class Preview(NamedTuple):
    """A submission preview."""

    source_id: str
    """Unique identifier for the source package in the file manager service."""

    checksum: str
    """URL-safe base64-encoded MD5 hash of the source package."""

    metadata: Optional['Metadata'] = None

    content: Optional['Content'] = None
    """The preview content, if available."""


class Metadata(NamedTuple):
    """Metadata about the preview."""

    added: datetime
    """Datetime when the preview was added."""

    checksum: str
    """URL-safe base64-encoded MD5 hash of the preview object."""

    size_bytes: int
    """Size of the preview."""


class Content(NamedTuple):
    """Content of the submission preview."""

    stream: IO[bytes]
    """
    An IO object, the ``read()`` method of which returns bytes.

    For example, a filepointer opened with ``rb``.
    """