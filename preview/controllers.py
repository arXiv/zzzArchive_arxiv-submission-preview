"""Provides request controllers for the submission preview service."""

from typing import Tuple, Any, Dict, List, IO, Union
from http import HTTPStatus

from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import InternalServerError

Response = Tuple[Union[Dict[str, Any], IO[bytes]], HTTPStatus, Dict[str, str]]


def service_status(params: MultiDict) -> Response:
    """
    Handle requests for the service status endpoint.

    Returns ``200 OK`` if the service is up and ready to handle requests.
    """
    return {'iam': 'ok'}, HTTPStatus.OK, {}


def get_preview_metadata(source_id: str, checksum: str) -> Response:
    ...


def get_preview_content(source_id: str, checksum: str) -> Response:
    ...


def deposit_preview(source_id: str, checksum: str) -> Response:
    ...