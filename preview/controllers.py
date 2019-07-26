"""Provides request controllers for the submission preview service."""

from typing import Tuple, Any, Dict, List, IO, Union, Optional
from http import HTTPStatus

from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import InternalServerError, BadRequest, Conflict

from arxiv.base import logging
from .services import store
from .domain import Preview, Metadata, Content

logger = logging.getLogger(__name__)


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


def deposit_preview(source_id: str, checksum: str, stream: IO[bytes],
                    content_type: Optional[str]) -> Response:
    """
    Handle a request to deposit the content of a preview.

    Parameters
    ----------
    source_id : str
        Unique identifier for the source package.
    checksum : str
        State of the source package to which this preview corresponds.
    stream : io.BytesIO
        Byte-stream from the request body.

    Returns
    -------
    dict
        Metadata about the deposit.
    int
        HTTP status code.
    dict
        Headers to add to the response.

    """
    if content_type is None:
        raise BadRequest('Must specify content type')
    st = store.PreviewStore.current_session()
    preview = Preview(source_id,
                      checksum,
                      content=Content(stream=stream,
                                      content_type=content_type))
    try:
        preview = st.deposit(preview)
    except store.DepositFailed as e:
        raise InternalServerError('An unexpected error occurred') from e
    except store.PreviewAlreadyExists as e:
        raise Conflict('Preview resource already exists') from e
    if preview.metadata is None:
        logger.error('Preview metadata not set')
        raise InternalServerError('An error occurred when storing preview')

    response_data = {'size_bytes': preview.metadata.size_bytes,
                     'checksum': preview.metadata.checksum,
                     'added': preview.metadata.added}
    headers = {'ETag': preview.metadata.checksum}
    return response_data, HTTPStatus.CREATED, headers