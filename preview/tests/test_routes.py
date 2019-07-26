"""Tests for :mod:`.routes`."""

import io
from unittest import TestCase, mock
from http import HTTPStatus as status
from flask import Flask

from .. import routes


class APITest(TestCase):
    def setUp(self):
        """We have an app."""
        self.app = Flask('test')
        self.app.register_blueprint(routes.api)
        self.client = self.app.test_client()


class TestServiceStatus(APITest):
    """The service status endpoint indicates that the service is available."""

    @mock.patch(f'{routes.__name__}.controllers.service_status')
    def test_get_status(self, mock_controller):
        """GET the status endpoint."""
        mock_controller.return_value = ({}, status.OK, {})
        response = self.client.get('/status')
        self.assertEqual(response.status_code, status.OK,
                         'Returns with status code set by controller')

    @mock.patch(f'{routes.__name__}.controllers.service_status')
    def test_post_status(self, mock_controller):
        """POST the status endpoint."""
        response = self.client.post('/status')
        self.assertEqual(response.status_code, status.METHOD_NOT_ALLOWED,
                         'POST method is 405 Method Not Allowed')

    @mock.patch(f'{routes.__name__}.controllers.service_status')
    def test_put_status(self, mock_controller):
        """PUT the status endpoint."""
        response = self.client.put('/status')
        self.assertEqual(response.status_code, status.METHOD_NOT_ALLOWED,
                         'PUT method is 405 Method Not Allowed')

    @mock.patch(f'{routes.__name__}.controllers.service_status')
    def test_delete_status(self, mock_controller):
        """DELETE the status endpoint."""
        response = self.client.delete('/status')
        self.assertEqual(response.status_code, status.METHOD_NOT_ALLOWED,
                         'DELETE method is 405 Method Not Allowed')


class TestPreviewMetadata(APITest):
    """The metadata endpoint returns details about the preview."""

    @mock.patch(f'{routes.__name__}.controllers.get_preview_metadata')
    def test_get_preview_metadata(self, mock_controller):
        """GET the preview metadata endpoint."""
        mock_controller.return_value = ({'foo': 'bar'}, status.OK, {})
        response = self.client.get('/preview/12345/asdf1234==')

        mock_controller.assert_called_with('12345', 'asdf1234==')
        self.assertEqual(response.status_code, status.OK,
                         'Returns with status code set by controller')
        self.assertEqual(response.headers['Content-type'],
                         'application/json',
                         'Content-type header indicates JSON response data')
        data = response.get_json()
        self.assertIsNotNone('Returns valid JSON')
        self.assertDictEqual(data, {'foo': 'bar'},
                             'Serializes the data returned by the controller')


    @mock.patch(f'{routes.__name__}.controllers.get_preview_metadata')
    def test_post_preview_metadata(self, mock_controller):
        """POST the preview metadata endpoint."""
        response = self.client.post('/preview/12345/asdf1234==')
        self.assertEqual(response.status_code, status.METHOD_NOT_ALLOWED,
                         'POST method is 405 Method Not Allowed')

    @mock.patch(f'{routes.__name__}.controllers.get_preview_metadata')
    def test_put_preview_metadata(self, mock_controller):
        """PUT the preview metadata endpoint."""
        response = self.client.put('/preview/12345/asdf1234==')
        self.assertEqual(response.status_code, status.METHOD_NOT_ALLOWED,
                         'PUT method is 405 Method Not Allowed')

    @mock.patch(f'{routes.__name__}.controllers.get_preview_metadata')
    def test_delete_preview_metadata(self, mock_controller):
        """DELETE the preview metadata endpoint."""
        response = self.client.delete('/preview/12345/asdf1234==')
        self.assertEqual(response.status_code, status.METHOD_NOT_ALLOWED,
                         'DELETE method is 405 Method Not Allowed')


class TestPreviewContent(APITest):
    """The content endpoint returns the content of the preview."""

    @mock.patch(f'{routes.__name__}.controllers.get_preview_content')
    def test_get_preview_content(self, mock_controller):
        """GET the preview content endpoint."""
        fake_content = b'fakecontent'
        headers = {'Content-type': 'application/pdf', 'ETag': 'foobar1=='}
        mock_controller.return_value = (
            io.BytesIO(fake_content),
            status.OK,
            headers
        )
        response = self.client.get('/preview/12345/asdf1234==/content',
                                   headers={'If-None-Match': 'foomatch'})

        mock_controller.assert_called_with('12345', 'asdf1234==', 'foomatch')
        self.assertEqual(response.status_code, status.OK,
                         'Returns with status code set by controller')
        self.assertEqual(response.headers['Content-type'],
                         headers['Content-type'],
                         'Content-type header indicates value returned'
                         ' by controller')
        data = response.data
        self.assertEqual(data, fake_content)
        self.assertEqual(response.headers['ETag'], 'foobar1==',
                         'Returns ETag header given by controller')

    @mock.patch(f'{routes.__name__}.controllers.get_preview_content')
    def test_post_preview_content(self, mock_controller):
        """POST the preview content endpoint."""
        response = self.client.post('/preview/12345/asdf1234==/content')
        self.assertEqual(response.status_code, status.METHOD_NOT_ALLOWED,
                         'POST method is 405 Method Not Allowed')

    @mock.patch(f'{routes.__name__}.controllers.get_preview_content')
    def test_delete_preview_metadata(self, mock_controller):
        """DELETE the preview content endpoint."""
        response = self.client.delete('/preview/12345/asdf1234==/content')
        self.assertEqual(response.status_code, status.METHOD_NOT_ALLOWED,
                         'DELETE method is 405 Method Not Allowed')

    @mock.patch(f'{routes.__name__}.controllers.deposit_preview')
    def test_put_preview_content(self, mock_controller):
        """PUT the preview content endpoint."""
        mock_controller.return_value = (
            {'foo': 'bar'},
            status.CREATED,
            {'ETag': 'foobar1=='}
        )

        fake_content = io.BytesIO(b'fakecontent')
        response = self.client.put(
            '/preview/12345/asdf1234==/content',
            data=fake_content,
            headers={'Content-type': 'application/pdf'}
        )

        source_id, checksum, stream, ctype = mock_controller.call_args[0]
        self.assertEqual(source_id, '12345')
        self.assertEqual(checksum, 'asdf1234==')
        self.assertEqual(stream.read(), b'fakecontent')

        self.assertEqual(response.status_code, status.CREATED,
                         'Returns with status code set by controller')
        self.assertEqual(response.headers['Content-type'],
                         'application/json',
                         'Return indicates JSON content type')
        data = response.get_json()
        self.assertIsNotNone(data, 'Returns JSON content')
        self.assertEqual(response.headers['ETag'], 'foobar1==',
                         'Returns ETag header given by controller')