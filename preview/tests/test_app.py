"""App tests."""

from unittest import TestCase, mock
from http import HTTPStatus as status
from moto import mock_s3

from ..factory import create_app
from ..services import PreviewStore, store


class TestServiceStatus(TestCase):

    @mock_s3
    def test_service_available(self):
        """The underlying storage service is available."""
        app = create_app()
        client = app.test_client()
        resp = client.get('/status')
        self.assertEqual(resp.status_code, status.OK)

    @mock_s3
    @mock.patch(f'{store.__name__}.PreviewStore.is_available')
    def test_service_unavailable(self, mock_is_available):
        """The underlying storage service is available."""
        app = create_app()
        mock_is_available.return_value = False
        client = app.test_client()
        resp = client.get('/status')
        self.assertEqual(resp.status_code, status.SERVICE_UNAVAILABLE)

