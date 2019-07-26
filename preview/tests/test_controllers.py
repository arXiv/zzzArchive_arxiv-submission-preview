"""Tests for :mod:`.controllers`."""

import io
from unittest import TestCase, mock
from datetime import datetime
from http import HTTPStatus as status

from pytz import UTC
from werkzeug.exceptions import BadRequest, InternalServerError, Conflict

from ..services import store
from ..domain import Preview, Metadata, Content
from .. import controllers


class TestDepositPreview(TestCase):
    """Tests for :func:`.controllers.deposit_preview` controller."""

    def setUp(self):
        """All requests are in the context of a source + checksum."""
        self.source_id = '12345'
        self.checksum = 'asdfqwert1=='
        self.stream = io.BytesIO(b'fakecontent')
        self.content_type = 'application/pdf'

    def test_no_content_type(self):
        """No content type is passed in the request."""
        with self.assertRaises(BadRequest):
            controllers.deposit_preview(self.source_id, self.checksum,
                                        self.stream, None)

    @mock.patch(f'{store.__name__}.PreviewStore.current_session')
    def test_deposit_fails(self, mock_current_session):
        """An error occurs when storing the preview."""
        mock_store = mock.MagicMock()
        mock_store.deposit.side_effect = store.DepositFailed
        mock_current_session.return_value = mock_store

        with self.assertRaises(InternalServerError):
            controllers.deposit_preview(self.source_id, self.checksum,
                                        self.stream, self.content_type)

    @mock.patch(f'{store.__name__}.PreviewStore.current_session')
    def test_already_exists(self, mock_current_session):
        """The preview already exists."""
        mock_store = mock.MagicMock()
        mock_store.deposit.side_effect = store.PreviewAlreadyExists
        mock_current_session.return_value = mock_store

        with self.assertRaises(Conflict):   # 409 Conflict
            controllers.deposit_preview(self.source_id, self.checksum,
                                        self.stream, self.content_type)

    @mock.patch(f'{store.__name__}.PreviewStore.current_session')
    def test_deposit_return_malformed(self, mock_current_session):
        """The store service returns malformed data."""
        mock_store = mock.MagicMock()
        # Doesn't add metadata.
        mock_store.deposit.side_effect = lambda obj: obj
        mock_current_session.return_value = mock_store

        with self.assertRaises(InternalServerError):
            controllers.deposit_preview(self.source_id, self.checksum,
                                        self.stream, self.content_type)

    @mock.patch(f'{store.__name__}.PreviewStore.current_session')
    def test_deposit_successful(self, mock_current_session):
        """The store service returns malformed data."""
        mock_store = mock.MagicMock()
        added = datetime.now(UTC)

        def mock_deposit(obj):
            """Deposit implementation sets metadata on Preview."""
            return Preview(source_id=obj.source_id,
                           checksum=obj.checksum,
                           metadata=Metadata(added=added,
                                             size_bytes=1_234,
                                             checksum='foopdfchex=='))

        mock_store.deposit.side_effect = mock_deposit
        mock_current_session.return_value = mock_store

        data, code, headers = \
            controllers.deposit_preview(self.source_id, self.checksum,
                                        self.stream, self.content_type)
        self.assertEqual(code, status.CREATED, 'Returns 201 Created')
        self.assertEqual(headers['ETag'], 'foopdfchex==',
                         'ETag is set to the preview checksum')
        self.assertDictEqual(data, {'size_bytes': 1_234,
                                    'checksum': 'foopdfchex==',
                                    'added': added},
                             'Returns metadata about the preview')

