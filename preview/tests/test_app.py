"""App tests."""

import io
import json
from unittest import TestCase, mock
from http import HTTPStatus as status

from moto import mock_s3
import jsonschema

from ..factory import create_app
from ..services import PreviewStore, store


class TestServiceStatus(TestCase):
    """Test the service status endpoint."""

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



class TestDeposit(TestCase):
    """Test depositing and retrieving a preview."""

    def setUp(self):
        """Load the JSON schema for response data."""
        with open('schema/resources/preview.json') as f:
            self.schema = json.load(f)

    @mock_s3
    def test_deposit_without_content_type(self):
        """Deposit a preview without hiccups."""
        app = create_app()
        client = app.test_client()
        content = io.BytesIO(b'foocontent')
        response = client.put('/1234/foohash1==/content', data=content)
        self.assertEqual(response.status_code, status.BAD_REQUEST,
                         'Returns 400 Bad Request')

    @mock_s3
    def test_deposit_with_unsupported_content_type(self):
        """Deposit a preview without hiccups."""
        app = create_app()
        client = app.test_client()
        content = io.BytesIO(b'foocontent')
        response = client.put('/1234/foohash1==/content', data=content,
                              headers={'Content-type': 'text/plain'})
        self.assertEqual(response.status_code, status.BAD_REQUEST,
                         'Returns 400 Bad Request')

    @mock_s3
    def test_deposit_ok(self):
        """Deposit a preview without hiccups."""
        app = create_app()
        client = app.test_client()
        content = io.BytesIO(b'foocontent')
        response = client.put('/1234/foohash1==/content', data=content,
                              headers={'Content-type': 'application/pdf'})
        response_data = response.get_json()
        self.assertIsNotNone(response_data, 'Returns valid JSON')
        self.assertEqual(response.status_code, status.CREATED,
                         'Returns 201 CREATED')
        self.assertEqual(response_data['checksum'],
                         '7b0ae08001dd093e79335b947f028b10',
                         'Returns S3 checksum of the preview content')
        self.assertEqual(response_data['checksum'], response.headers['ETag'],
                         'Includes ETag header with checksum as well')

        try:
            jsonschema.validate(response_data, self.schema)
        except jsonschema.ValidationError as e:
            self.fail(f'Failed to validate: {e}')

    @mock_s3
    def test_deposit_already_exists(self):
        """Deposit a preview that already exists."""
        app = create_app()
        client = app.test_client()
        content = io.BytesIO(b'foocontent')
        client.put('/1234/foohash1==/content', data=content,
                              headers={'Content-type': 'application/pdf'})
        new_content = io.BytesIO(b'barcontent')
        response = client.put('/1234/foohash1==/content', data=new_content,
                              headers={'Content-type': 'application/pdf'})
        self.assertEqual(response.status_code, status.CONFLICT,
                         'Returns 409 Conflict')

    @mock_s3
    def test_deposit_already_exists_overwrite(self):
        """Deposit a preview that already exists, with overwrite enabled."""
        app = create_app()
        client = app.test_client()
        content = io.BytesIO(b'foocontent')
        client.put('/1234/foohash1==/content', data=content,
                              headers={'Content-type': 'application/pdf'})
        new_content = io.BytesIO(b'barcontent')
        response = client.put('/1234/foohash1==/content', data=new_content,
                              headers={'Content-type': 'application/pdf',
                                       'Overwrite': 'true'})
        self.assertEqual(response.status_code, status.CREATED,
                         'Returns 201 Created')
        response_data = response.get_json()
        try:
            jsonschema.validate(response_data, self.schema)
        except jsonschema.ValidationError as e:
            self.fail(f'Failed to validate: {e}')

    @mock_s3
    def test_retrieve_metadata(self):
        """Retrieve a preview without hiccups."""
        app = create_app()
        client = app.test_client()
        content = io.BytesIO(b'foocontent')
        client.put('/1234/foohash1==/content', data=content,
                   headers={'Content-type': 'application/pdf'})
        response = client.get('/1234/foohash1==')
        response_data = response.get_json()

        self.assertIsNotNone(response_data, 'Returns valid JSON')
        self.assertEqual(response.status_code, status.OK, 'Returns 200 OK')
        self.assertEqual(response_data['checksum'],
                         '7b0ae08001dd093e79335b947f028b10',
                         'Returns S3 checksum of the preview content')
        self.assertEqual(response_data['checksum'], response.headers['ETag'],
                         'Includes ETag header with checksum as well')

        try:
            jsonschema.validate(response_data, self.schema)
        except jsonschema.ValidationError as e:
            self.fail(f'Failed to validate: {e}')

    @mock_s3
    def test_retrieve_nonexistant_metadata(self):
        """Retrieve metadata for a non-existant preview"""
        app = create_app()
        client = app.test_client()
        content = io.BytesIO(b'foocontent')

        response = client.get('/1234/foohash1==')
        response_data = response.get_json()

        self.assertIsNotNone(response_data, 'Returns valid JSON')
        self.assertEqual(response.status_code, status.NOT_FOUND,
                         'Returns 404 Not Found')

    @mock_s3
    def test_retrieve_nonexistant_content(self):
        """Retrieve content for a non-existant preview"""
        app = create_app()
        client = app.test_client()
        content = io.BytesIO(b'foocontent')

        response = client.get('/1234/foohash1==/content')

        self.assertEqual(response.status_code, status.NOT_FOUND,
                         'Returns 404 Not Found')

    @mock_s3
    def test_retrieve_content(self):
        """Retrieve preview content without hiccups."""
        app = create_app()
        client = app.test_client()
        content = io.BytesIO(b'foocontent')
        client.put('/1234/foohash1==/content', data=content,
                   headers={'Content-type': 'application/pdf'})
        response = client.get('/1234/foohash1==/content')

        self.assertEqual(response.data, b'foocontent')
        self.assertEqual(response.headers['Content-Type'], 'application/pdf')
        self.assertEqual(response.status_code, status.OK, 'Returns 200 OK')
        self.assertEqual(response.headers['ETag'],
                         '7b0ae08001dd093e79335b947f028b10',
                         'Includes ETag header with checksum as well')

    @mock_s3
    def test_retrieve_with_none_match_matches(self):
        """Retrieve preview content with If-None-Match header."""
        app = create_app()
        client = app.test_client()
        content = io.BytesIO(b'foocontent')
        resp = client.put('/1234/foohash1==/content', data=content,
                          headers={'Content-type': 'application/pdf'})
        headers = {'If-None-Match': resp.headers['ETag']}
        response = client.get('/1234/foohash1==/content', headers=headers)

        self.assertEqual(response.status_code, status.NOT_MODIFIED,
                         'Returns 304 Not Modified')

    @mock_s3
    def test_retrieve_with_none_match_no_match(self):
        """Retrieve preview content with If-None-Match header."""
        app = create_app()
        client = app.test_client()
        content = io.BytesIO(b'foocontent')
        resp = client.put('/1234/foohash1==/content', data=content,
                          headers={'Content-type': 'application/pdf'})
        headers = {'If-None-Match': resp.headers['ETag'] + 'foo'}
        response = client.get('/1234/foohash1==/content', headers=headers)

        self.assertEqual(response.status_code, status.OK, 'Returns 200 OK')

