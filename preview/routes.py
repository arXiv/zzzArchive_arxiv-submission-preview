"""Provides the API blueprint for the submission preview service."""

import io
from http import HTTPStatus as status
from typing import Dict, Any, IO, Optional

from flask import Blueprint, Response, request, make_response, send_file, \
    current_app
from flask.json import jsonify
from werkzeug.exceptions import RequestEntityTooLarge, BadRequest

from arxiv.users import auth  # pylint: disable=no-name-in-module

from . import controllers


api = Blueprint('api', __name__, url_prefix='')


@api.route('/status', methods=['GET'])
def service_status() -> Response:
    """
    Service status endpoint.

    Returns ``200 OK`` if the service is up and ready to handle requests.
    """
    data, code, headers = controllers.service_status(request.args)
    response: Response = make_response(jsonify(data), code, headers)
    return response


@api.route('/<source_id>/<checksum>', methods=['HEAD'])
@auth.decorators.scoped(auth.scopes.READ_PREVIEW)
def check_preview_exists(source_id: str, checksum: str) -> Response:
    """Verify that the preview exists."""
    data, code, headers = controllers.check_preview_exists(source_id, checksum)
    response: Response = make_response(jsonify(data), code, headers)
    return response


@api.route('/<source_id>/<checksum>', methods=['GET'])
@auth.decorators.scoped(auth.scopes.READ_PREVIEW)
def get_preview_metadata(source_id: str, checksum: str) -> Response:
    """Returns a JSON document describing the preview."""
    data, code, headers = controllers.get_preview_metadata(source_id, checksum)
    response: Response = make_response(jsonify(data), code, headers)
    return response


@api.route('/<source_id>/<checksum>/content', methods=['GET'])
@auth.decorators.scoped(auth.scopes.READ_PREVIEW)
def get_preview_content(source_id: str, checksum: str) -> Response:
    """Returns the preview content (e.g. as ``application/pdf``)."""
    none_match = request.headers.get('If-None-Match')
    data, code, headers = \
        controllers.get_preview_content(source_id, checksum, none_match)
    if code == status.OK:
        response: Response = send_file(data, mimetype=headers['Content-type'])
    else:
        response = make_response(jsonify(data))
    response = _update_headers(response, headers)
    response.status_code = code
    return response


@api.route('/<source_id>/<checksum>/content', methods=['PUT'])
@auth.decorators.scoped(auth.scopes.CREATE_PREVIEW)
def deposit_preview(source_id: str, checksum: str) -> Response:
    """Creates a new preview resource at the specified key."""
    content_checksum: Optional[str] = request.headers.get('ETag', None)
    overwrite = bool(request.headers.get('Overwrite', 'false') == 'true')

    stream: IO[bytes]
    if request.headers.get('Content-type') is not None:
        length = int(request.headers.get('Content-length', 0))
        if length == 0:
            raise BadRequest('Body empty or content-length not set')
        max_length = int(current_app.config['MAX_PAYLOAD_SIZE_BYTES'])
        if length > max_length:
            raise RequestEntityTooLarge(f'Body exceeds size of {max_length}')
        stream = io.BytesIO(request.data)
    else:
        # DANGER! request.stream will ONLY be available if (a) the content-type
        # header is not passed and (b) we have not accessed the body via any
        # other means, e.g. ``.data``, ``.json``, etc.
        stream = request.stream   # type: ignore
    data, code, headers = controllers.deposit_preview(
        source_id, checksum, stream,
        overwrite=overwrite,
        content_checksum=content_checksum
    )
    response: Response = make_response(jsonify(data), code, headers)
    return response


def _update_headers(response: Response, headers: Dict[str, Any]) -> Response:
    for key, value in headers.items():
        if key in response.headers:     # Avoid duplicate headers.
            response.headers.remove(key)   # type: ignore
        response.headers.add(key, value)   # type: ignore
    return response
