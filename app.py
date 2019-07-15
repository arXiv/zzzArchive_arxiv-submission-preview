"""Flask app entrypoint for development purposes."""

from preview.factory import create_app

app = create_app()
