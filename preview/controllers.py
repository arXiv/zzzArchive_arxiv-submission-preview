"""Provides request controllers for the submission preview service."""

from typing import Tuple, Any, Dict, List, IO, Union, Optional
from http import HTTPStatus

from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import InternalServerError, BadRequest, Conflict, \
    NotFound, ServiceUnavailable

from arxiv.base import logging
from .services import store
from .domain import Preview, Metadata, Content

logger = logging.getLogger(__name__)

ResponseData = Optional[Union[Dict[str, Any], IO[bytes]]]
Response = Tuple[ResponseData, HTTPStatus, Dict[str, str]]


def service_status(*args: Any, **kwargs: Any) -> Response:
    """
    Handle requests for the service status endpoint.

    Returns ``200 OK`` if the service is up and ready to handle requests.

    Parameters
    ----------
    args : *args
        Unused.
    kwargs : **kwargs
        Unused.

    Returns
    -------
    dict
        Metadata about the deposit.
    int
        HTTP status code.
    dict
        Headers to add to the response.

    Raises
    ------
    :class:`.ServiceUnavaiable`
        Raised when one or more upstream services are not available.

    """
    st = store.PreviewStore.current_session()
    if not st.is_available():
        raise ServiceUnavailable('Cannot connect to store')
    return {'iam': 'ok'}, HTTPStatus.OK, {}


def get_preview_metadata(source_id: str, checksum: str) -> Response:
    """
    Handle request for preview metadata.

    Parameters
    ----------
    source_id : str
        Unique identifier for the source package.
    checksum : str
        State of the source package to which this preview corresponds.

    Returns
    -------
    dict
        Metadata about the deposit.
    int
        HTTP status code.
    dict
        Headers to add to the response.

    Raises
    ------
    :class:`.NotFound`
        Raised when a non-existant preview is requested.

    """
    st = store.PreviewStore.current_session()
    try:
        metadata = st.get_metadata(source_id, checksum)
    except store.DoesNotExist as e:
        raise NotFound('No preview available') from e

    data = {'added': metadata.added,
            'checksum': metadata.checksum,
            'size_bytes': metadata.size_bytes}
    headers = {'ETag': metadata.checksum}
    return data, HTTPStatus.OK, headers


def get_preview_content(source_id: str, checksum: str,
                        none_match: Optional[str] = None) -> Response:
    """
    Handle request for preview content.

    Parameters
    ----------
    source_id : str
        Unique identifier for the source package.
    checksum : str
        State of the source package to which this preview corresponds.
    none_match : str or None
        If not None, will return 304 Not Modified if the current preview
        checksum matches.

    Returns
    -------
    io.BytesIO
        Stream containing the preview content.
    int
        HTTP status code.
    dict
        Headers to add to the response.

    Raises
    ------
    :class:`.NotFound`
        Raised when a non-existant preview is requested.
    :class:`.InternalServerError`
        Raised when preview metadata or content are not loaded correctly.

    """
    st = store.PreviewStore.current_session()
    try:
        if none_match is not None:
            preview_checksum = st.get_preview_checksum(source_id, checksum)
            if none_match == preview_checksum:
                headers = {'ETag': preview_checksum}
                return None, HTTPStatus.NOT_MODIFIED, headers

        preview = st.get_preview(source_id, checksum)
    except store.DoesNotExist as e:
        raise NotFound('No preview available') from e

    if preview.metadata is None or preview.content is None:
        raise InternalServerError('Unexpected error loading content')

    headers = {'ETag': preview.metadata.checksum,
               'Content-type': 'application/pdf',}
    return preview.content.stream, HTTPStatus.OK, headers


def deposit_preview(source_id: str, checksum: str, stream: IO[bytes],
                    content_type: Optional[str],
                    overwrite: bool = False) -> Response:
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
    content_type : str
        Value of the ``Content-type`` request header.
    overwrite : bool
        Value of the ``Overwrite`` request header.

    Returns
    -------
    dict
        Metadata about the deposit.
    int
        HTTP status code.
    dict
        Headers to add to the response.

    Raises
    ------
    :class:`.BadRequest`
        Raised when the request is incomplete, specifically when the
        ``Content-type`` header is missing or unsupported.
    :class:`.InternalServerError`
        Raised when there is a problem storing the preview.
    :class:`.Conflict`
        Raised when content already exists for the preview, and ``overwrite``
        is ``False``.

    """
    if content_type is None or content_type != 'application/pdf':
        logger.info('Request is missing content-type header')
        raise BadRequest(f'Invalid content type: {content_type}')
    st = store.PreviewStore.current_session()
    preview = Preview(source_id, checksum, content=Content(stream=stream))
    try:
        preview = st.deposit(preview, overwrite=overwrite)
    except store.DepositFailed as e:
        raise InternalServerError('An unexpected error occurred') from e
    except store.PreviewAlreadyExists as e:
        raise Conflict('Preview resource already exists') from e
    if preview.metadata is None:
        logger.error('Preview metadata not set')
        raise InternalServerError('An error occurred when storing preview')

    response_data = {'checksum': preview.metadata.checksum,
                     'added': preview.metadata.added,
                     'size_bytes': preview.metadata.size_bytes}
    headers = {'ETag': preview.metadata.checksum}
    return response_data, HTTPStatus.CREATED, headers