"""Web Server Gateway Interface entry-point."""

import os
from preview.factory import create_app

__flask_app__ = create_app()


def application(environ, start_response):
    """WSGI application factory."""
    for key, value in environ.items():
        if type(value) is str and key != 'SERVER_NAME':
            os.environ[key] = value
            if key in __flask_app__.config:
                __flask_app__.config[key] = value
    return __flask_app__(environ, start_response)
