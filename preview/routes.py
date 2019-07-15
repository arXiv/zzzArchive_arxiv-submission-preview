"""Provides the API blueprint for the submission preview service."""

from flask import Blueprint, Response, request, make_response
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
