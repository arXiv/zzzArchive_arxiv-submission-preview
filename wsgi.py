"""Web Server Gateway Interface entry-point."""

import os
from typing import Optional

from flask import Flask

from preview.factory import create_app

__flask_app__: Optional[Flask] = None


def application(environ, start_response):
    """WSGI application factory."""
    global __flask_app__
    for key, value in environ.items():
        if type(value) is str and key != 'SERVER_NAME':
            os.environ[key] = value
            if __flask_app__ is not None and key in __flask_app__.config:
                __flask_app__.config[key] = value
    if __flask_app__ is None:
        __flask_app__ = create_app()
    return __flask_app__(environ, start_response)
