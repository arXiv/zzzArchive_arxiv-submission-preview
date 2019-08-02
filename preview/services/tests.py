"""Tests for :mod:`.services.store`."""

import io
from unittest import TestCase, mock
from moto import mock_s3
import boto3

from . import store
from ..domain import Preview, Metadata, Content


class TestStorePreview(TestCase):
    """Test storing and retrieving a preview."""

    @mock.patch(f'{store.__name__}.get_application_config')
    def setUp(self, mock_get_config):
        """Get a new session with the storage."""
        mock_get_config.return_value = {
            'S3_BUCKET': 'foobucket',
            'S3_VERIFY': False,
            'AWS_REGION': 'us-east-1',
            'S3_ENDPOINT': None,
            'AWS_ACCESS_KEY_ID': 'fookkey',
            'AWS_SECRET_ACCESS_KEY': 'foosecret'
        }
        self.store = store.PreviewStore.current_session()

    @mock_s3
    def test_deposit(self):
        """Deposit a preview and then load it."""
        self.store.initialize()
        stream = io.BytesIO(b'foocontent')
        preview = Preview(source_id='1234',
                          checksum='foochex==',
                          content=Content(stream=stream))
        after = self.store.deposit(preview)

        self.assertIsNotNone(after.metadata, 'Metadata member is set')
        self.assertEqual(after.metadata.size_bytes, 10, 'Calculates size')
        self.assertEqual(after.metadata.checksum,
                         'ewrggAHdCT55M1uUfwKLEA==',
                         'Calculates checksum')

        metadata = self.store.get_metadata('1234', 'foochex==')
        self.assertEqual(metadata.size_bytes, after.metadata.size_bytes,
                         'Loads size of the preview')
        self.assertEqual(metadata.checksum, after.metadata.checksum,
                         'Loads checksum of the preview')

        self.assertEqual(self.store.get_preview_checksum('1234', 'foochex=='),
                         after.metadata.checksum,
                         'Returns the S3 checksum of the preview')

        loaded = self.store.get_preview('1234', 'foochex==')
        self.assertEqual(loaded.metadata.size_bytes, after.metadata.size_bytes,
                         'Loads size of the preview')
        self.assertEqual(loaded.metadata.checksum, after.metadata.checksum,
                         'Loads checksum of the preview')

        self.assertEqual(loaded.content.stream.read(), b'foocontent',
                         'Loads original content')

    @mock_s3
    def test_retrieve_nonexistant(self):
        """Deposit a preview and then load it."""
        self.store.initialize()
        with self.assertRaises(store.DoesNotExist):
            self.store.get_metadata('1234', 'foochex==')

        with self.assertRaises(store.DoesNotExist):
            self.store.get_preview_checksum('1234', 'foochex==')

        with self.assertRaises(store.DoesNotExist):
            self.store.get_preview('1234', 'foochex==')
