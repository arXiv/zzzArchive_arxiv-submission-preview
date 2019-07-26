"""Provides the API blueprint for the submission preview service."""

from typing import Dict, Any

from flask import Blueprint, Response, request, make_response, send_file
from flask.json import jsonify

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


@api.route('/preview/<source_id>/<checksum>', methods=['GET'])
def get_preview_metadata(source_id: str, checksum: str) -> Response:
    """Returns a JSON document describing the preview."""
    data, code, headers = controllers.get_preview_metadata(source_id, checksum)
    response: Response = make_response(jsonify(data), code, headers)
    return response


@api.route('/preview/<source_id>/<checksum>/content', methods=['GET'])
def get_preview_content(source_id: str, checksum: str) -> Response:
    """Returns the preview content (e.g. as ``application/pdf``)."""
    none_match = request.headers.get('If-None-Match')
    data, code, headers = \
        controllers.get_preview_content(source_id, checksum, none_match)
    response: Response = send_file(data, mimetype=headers['Content-type'])
    response = _update_headers(response, headers)
    response.status_code = code
    return response


@api.route('/preview/<source_id>/<checksum>/content', methods=['PUT'])
def deposit_preview(source_id: str, checksum: str) -> Response:
    """Creates a new preview resource at the specified key."""
    content_type = request.headers.get('Content-type')
    data, code, headers = controllers.deposit_preview(source_id, checksum,
                                                      request.stream,
                                                      content_type)
    response: Response = make_response(jsonify(data), code, headers)
    return response


def _update_headers(response: Response, headers: Dict[str, Any]) -> Response:
    for key, value in headers.items():
        if key in response.headers:     # Avoid duplicate headers.
            response.headers.remove(key)   # type: ignore
        response.headers.add(key, value)   # type: ignore
    return response
