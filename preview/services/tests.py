"""Tests for :mod:`.services.store`."""

from unittest import TestCase
from moto import mock_s3

from . import store
from ..domain import Preview, Metadata, Content


class TestStorePreview(TestCase):
    """Test storing a preview."""

    # @mock_s3
    # def test_store(self):
    #     """So it begins."""
    #     st = store.PreviewStore.current_session()


