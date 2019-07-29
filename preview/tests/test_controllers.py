"""Tests for :mod:`.controllers`."""

import io
from unittest import TestCase, mock
from datetime import datetime
from http import HTTPStatus as status

from pytz import UTC
from werkzeug.exceptions import BadRequest, InternalServerError, Conflict, \
    NotFound, ServiceUnavailable

from ..services import store
from ..domain import Preview, Metadata, Content
from .. import controllers


class TestStatusEndpoint(TestCase):
    """Status endpoint should reflect availability of storage integration."""

    @mock.patch(f'{controllers.__name__}.store.PreviewStore.current_session')
    def test_store_is_unavailable(self, mock_current_session):
        """Storage service is unavailable."""
        mock_store = mock.MagicMock()
        mock_store.is_available.return_value = False
        mock_current_session.return_value = mock_store
        with self.assertRaises(ServiceUnavailable):
            controllers.service_status()

    @mock.patch(f'{controllers.__name__}.store.PreviewStore.current_session')
    def test_store_is_available(self, mock_current_session):
        """Storage service is available."""
        mock_store = mock.MagicMock()
        mock_store.is_available.return_value = True
        mock_current_session.return_value = mock_store
        _, code, _ = controllers.service_status()
        self.assertEqual(code, status.OK)



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
                                             checksum='foopdfchex==',
                                             size_bytes=1_234))

        mock_store.deposit.side_effect = mock_deposit
        mock_current_session.return_value = mock_store

        data, code, headers = \
            controllers.deposit_preview(self.source_id, self.checksum,
                                        self.stream, self.content_type)
        self.assertEqual(code, status.CREATED, 'Returns 201 Created')
        self.assertEqual(headers['ETag'], 'foopdfchex==',
                         'ETag is set to the preview checksum')
        self.assertDictEqual(data, {'checksum': 'foopdfchex==',
                                    'added': added},
                             'Returns metadata about the preview')



class TestRetrievePreviewMetadata(TestCase):
    """Tests for :func:`.controllers.get_preview_metadata` controller."""

    def setUp(self):
        """All requests are in the context of a source + checksum."""
        self.source_id = '12345'
        self.checksum = 'asdfqwert1=='
        self.stream = io.BytesIO(b'fakecontent')
        self.content_type = 'application/pdf'

    @mock.patch(f'{store.__name__}.PreviewStore.current_session')
    def test_does_not_exist(self, mock_current_session):
        """The requested preview does not exist."""
        mock_store = mock.MagicMock()
        mock_store.get_metadata.side_effect = store.DoesNotExist
        mock_current_session.return_value = mock_store

        with self.assertRaises(NotFound):
            controllers.get_preview_metadata(self.source_id, self.checksum)

    @mock.patch(f'{store.__name__}.PreviewStore.current_session')
    def test_exists(self, mock_current_session):
        """The requested preview does exist."""
        added = datetime.now(UTC)
        mock_store = mock.MagicMock()
        mock_store.get_metadata.return_value = \
            Metadata(added=added, checksum='foopdfchex==', size_bytes=1_234)
        mock_current_session.return_value = mock_store

        data, code, headers = \
            controllers.get_preview_metadata(self.source_id, self.checksum)
        self.assertEqual(code, status.OK, 'Returns 200 OK')
        self.assertEqual(headers['ETag'], 'foopdfchex==',
                         'ETag is set to the preview checksum')
        self.assertDictEqual(data, {'checksum': 'foopdfchex==',
                                    'added': added},
                             'Returns metadata about the preview')

class TestRetrievePreviewContent(TestCase):
    """Tests for :func:`.controllers.get_preview_content` controller."""

    def setUp(self):
        """All requests are in the context of a source + checksum."""
        self.source_id = '12345'
        self.checksum = 'asdfqwert1=='
        self.stream = io.BytesIO(b'fakecontent')
        self.content_type = 'application/pdf'

    @mock.patch(f'{store.__name__}.PreviewStore.current_session')
    def test_does_not_exist(self, mock_current_session):
        """The requested preview does not exist."""
        mock_store = mock.MagicMock()
        mock_store.get_preview.side_effect = store.DoesNotExist
        mock_current_session.return_value = mock_store

        with self.assertRaises(NotFound):
            controllers.get_preview_content(self.source_id, self.checksum)

    @mock.patch(f'{store.__name__}.PreviewStore.current_session')
    def test_exists(self, mock_current_session):
        """The requested preview does exist."""
        added = datetime.now(UTC)
        mock_store = mock.MagicMock()
        mock_store.get_preview.return_value = Preview(
            source_id=self.source_id,
            checksum=self.checksum,
            metadata=Metadata(added=added, checksum='foopdfchex==',
                              size_bytes=1_234),
            content=Content(stream=io.BytesIO(b'fakecontent'))
        )
        mock_current_session.return_value = mock_store

        data, code, headers = \
            controllers.get_preview_content(self.source_id, self.checksum)
        self.assertEqual(code, status.OK, 'Returns 200 OK')
        self.assertEqual(headers['ETag'], 'foopdfchex==',
                         'ETag is set to the preview checksum')
        self.assertEqual(data.read(), b'fakecontent', 'Returns content stream')

    @mock.patch(f'{store.__name__}.PreviewStore.current_session')
    def test_if_none_match_matches(self, mock_current_session):
        """Request includes if-none-match param with matching etag."""
        added = datetime.now(UTC)
        mock_store = mock.MagicMock()
        mock_store.get_preview_checksum.return_value = 'foopdfchex=='
        mock_current_session.return_value = mock_store

        data, code, headers = \
            controllers.get_preview_content(self.source_id, self.checksum,
                                            'foopdfchex==')
        self.assertEqual(code, status.NOT_MODIFIED, 'Returns 304 Not Modified')
        self.assertEqual(headers['ETag'], 'foopdfchex==',
                         'ETag is set to the preview checksum')
        self.assertIsNone(data, 'Returns no data')

    @mock.patch(f'{store.__name__}.PreviewStore.current_session')
    def test_if_none_match_does_not_match(self, mock_current_session):
        """Request includes if-none-match param with non-matching etag."""
        added = datetime.now(UTC)
        mock_store = mock.MagicMock()
        mock_store.get_preview_checksum.return_value = 'foopdfchex=='
        mock_store.get_preview.return_value = Preview(
            source_id=self.source_id,
            checksum=self.checksum,
            metadata=Metadata(added=added, checksum='foopdfchex==',
                              size_bytes=1_234),
            content=Content(stream=io.BytesIO(b'fakecontent'))
        )
        mock_current_session.return_value = mock_store

        data, code, headers = \
            controllers.get_preview_content(self.source_id, self.checksum,
                                            'foopdfchey==')
        self.assertEqual(code, status.OK, 'Returns 200 OK')
        self.assertEqual(headers['ETag'], 'foopdfchex==',
                         'ETag is set to the preview checksum')
        self.assertEqual(data.read(), b'fakecontent', 'Returns content stream')