"""Provides an application factory for the submission preview service."""

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException, Forbidden, Unauthorized, \
    BadRequest, MethodNotAllowed, InternalServerError, NotFound, \
    ServiceUnavailable

from arxiv import vault
from arxiv.base import Base, logging
from arxiv.base.middleware import wrap, request_logs
from arxiv.users import auth

from .services import PreviewStore
from . import routes
from .encode import PreviewEncoder


def create_app() -> Flask:
    """Create a new API application."""
    app = Flask('preview')
    app.json_encoder = PreviewEncoder
    app.config.from_pyfile('config.py')

    Base(app)
    auth.Auth(app)

    # Set up the API.
    app.register_blueprint(routes.api)
    register_error_handlers(app)

    # Add WSGI middlewares.
    middleware = [request_logs.ClassicLogsMiddleware,
                  auth.middleware.AuthMiddleware]
    if app.config['VAULT_ENABLED']:
        middleware.insert(0, vault.middleware.VaultMiddleware)
    wrap(app, middleware)

    # Make sure that we have all of the secrets that we need to run.
    if app.config['VAULT_ENABLED']:
        app.middlewares['VaultMiddleware'].update_secrets({})

    # Initialize upstream services.
    PreviewStore.init_app(app)
    if app.config['WAIT_FOR_SERVICES']:
        with app.app_context():  # type: ignore
            PreviewStore.current_session().initialize()
    return app


def register_error_handlers(app: Flask) -> None:
    """Register error handlers for the Flask app."""
    app.errorhandler(Forbidden)(jsonify_exception)
    app.errorhandler(Unauthorized)(jsonify_exception)
    app.errorhandler(BadRequest)(jsonify_exception)
    app.errorhandler(InternalServerError)(jsonify_exception)
    app.errorhandler(ServiceUnavailable)(jsonify_exception)
    app.errorhandler(NotFound)(jsonify_exception)
    app.errorhandler(MethodNotAllowed)(jsonify_exception)


def jsonify_exception(error: HTTPException) -> Response:
    """Render exceptions as JSON."""
    exc_resp = error.get_response()
    response: Response = jsonify(reason=error.description)
    response.status_code = exc_resp.status_code
    return response
