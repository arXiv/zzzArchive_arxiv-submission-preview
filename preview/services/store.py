"""
Storage service module for submission preview content and metadata.

Requirements
------------
1. Provides methods for storing and retrieving submission preview content and
   associated metadata.
2. Must be thread-safe.

  - Should use the `Flask ``g`` object
    <https://flask.palletsprojects.com/en/1.1.x/appcontext/#storing-data>`_ to
    store request-specific state, such as a connection object.
  - Provides a function or classmethod to obtain an instance of the service
    that is bound to the request or application context.

3. Provides a method for verifying read/write connection to the S3 bucket, that
   can be used in status checks.
4. Raises semantically informative exceptions that are defined within this
   module.


Constraints
-----------
1. Should be implemented using boto3.
2. Must be consistent with the patterns described `here
   <https://arxiv.github.io/arxiv-arxitecture/crosscutting/services.html#service-integrations>`_.


"""
import binascii
import io
from base64 import urlsafe_b64encode, urlsafe_b64decode
from datetime import datetime
from hashlib import md5
from typing import IO, Tuple, Optional, Dict, Any, Union

import boto3
import botocore
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from botocore.exceptions import ClientError
from flask import Flask
from pytz import UTC
from typing_extensions import TypedDict, Literal

from arxiv.base import logging
from arxiv.base.globals import get_application_global, get_application_config

from ..domain import Content, Preview, Metadata

logger = logging.getLogger(__name__)

Num = Union[int, float]


class HeadResponse(TypedDict):
    """Expected response to HEAD object requests."""

    ETag: str
    LastModified: datetime
    ContentLength: int


class GetResponse(TypedDict):
    """Expected response to GET object requests."""

    ETag: str
    LastModified: datetime
    ContentLength: int
    Body: IO[bytes]


class StreamMonitor(io.BytesIO):
    """Wraps a stream to calculate checksum and size as the stream is read."""

    def __init__(self, stream: IO[bytes]) -> None:
        """Initialize md5 hash and size."""
        self._stream = stream
        self._md5 = md5()
        self.size_bytes = 0
        super().__init__()

    def seekable(self) -> Literal[False]:
        """Indicate that this is a non-seekable stream."""
        return False

    def readable(self) -> Literal[True]:
        """Indicate that it *is* a readable stream."""
        return True

    def read(self, size: Optional[int] = -1) -> bytes:
        """Update the hash and size as the stream is read."""
        if size is None:
            size = -1
        chunk = self._stream.read(size)
        if len(chunk) != 0:
            self._md5.update(chunk)
            self.size_bytes += len(chunk)
        return chunk

    @property
    def checksum(self) -> str:
        """Get the url-safe base64-encoded MD5 hash of the stream content."""
        return urlsafe_b64encode(self._md5.digest()).decode('utf-8')
        # return self._md5.hexdigest()


class NoSuchBucket(Exception):
    """The configured bucket does not exist."""


class DoesNotExist(Exception):
    """An attempt was made to retrieve a non-existant preview."""


class DepositFailed(Exception):
    """An attempt to deposit a preview was not successful."""


class PreviewAlreadyExists(Exception):
    """An attempt to deposit an existing preview was made."""


# TODO: enough of this is reused from other places that we may want to consider
# adding the boilerplate to ``arxiv.integration``.
class PreviewStore:
    """Service integration for storing previews in S3."""

    def __init__(self, bucket: str, verify: bool = False,
                 region_name: Optional[str] = None,
                 endpoint_url: Optional[str] = None,
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None) -> None:
        """Initialize with connection config parameters."""
        self._bucket = bucket
        self._region_name = region_name
        self._endpoint_url = endpoint_url
        self._verify = verify
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self.client = self._new_client()

    def _new_client(self, config: Optional[Config] = None) -> boto3.client:
        # Only add credentials to the client if they are explicitly set.
        # If they are not set, boto3 falls back to environment variables and
        # credentials files.
        params: Dict[str, Any] = {'region_name': self._region_name}
        if self._aws_access_key_id and self._aws_secret_access_key:
            params['aws_access_key_id'] = self._aws_access_key_id
            params['aws_secret_access_key'] = self._aws_secret_access_key
        if self._endpoint_url:
            params['endpoint_url'] = self._endpoint_url
            params['verify'] = self._verify
        logger.debug('new client with params %s', params)
        return boto3.client('s3', **params)

    def _handle_client_error(self, exc: ClientError) -> None:
        logger.error('error: %s', str(exc.response))
        if exc.response['Error']['Code'] == 'NoSuchBucket':
            logger.error('Caught ClientError: NoSuchBucket')
            raise NoSuchBucket(f'{self._bucket} does not exist') from exc
        if exc.response['Error']['Code'] == "NoSuchKey" \
                or exc.response['Error']['Code'] == '404':
            raise DoesNotExist(f'No such object in {self._bucket}') from exc
        logger.error('Unhandled ClientError: %s', exc)
        raise RuntimeError('Unhandled ClientError') from exc

    def __hash__(self) -> int:
        """Generate a unique hash for this store session using its config."""
        return hash((self._bucket, self._region_name, self._endpoint_url,
                     self._verify, self._aws_access_key_id,
                     self._aws_secret_access_key))

    def is_available(self, retries: int = 0, read_timeout: Num = 5,
                     connect_timeout: Num = 5) -> bool:
        """Check whether we can write to the S3 bucket."""
        try:
            self._test_put(retries=retries, read_timeout=read_timeout,
                           connect_timeout=connect_timeout)
            logger.debug('S3 is available')
            return True
        except RuntimeError:
            logger.debug('S3 is not available')
            return False

    def _test_put(self, retries: int = 0, read_timeout: int = 5,
                  connect_timeout: int = 5) -> None:
        """Test the connection to S3 by putting a tiny object."""
        # Use a new client with a short timeout and no retries by default; we
        # want to fail fast here.
        config = Config(retries={'max_attempts': retries},
                        read_timeout=read_timeout,
                        connect_timeout=connect_timeout)
        client = self._new_client(config=config)
        try:
            logger.info('trying to put to bucket %s', self._bucket)
            client.put_object(Body=b'test', Bucket=self._bucket, Key='stat')
        except ClientError as e:
            logger.error('Error when calling store: %s', e)
            self._handle_client_error(e)

    def _wait_for_bucket(self, retries: int = 0, delay: int = 0) -> None:
        """Wait for the bucket to available."""
        try:
            waiter = self.client.get_waiter('bucket_exists')
            waiter.wait(
                Bucket=self._bucket,
                WaiterConfig={
                    'Delay': delay,
                    'MaxAttempts': retries
                }
            )
        except ClientError as exc:
            self._handle_client_error(exc)

    def initialize(self) -> None:
        """Perform initial checks, e.g. at application start-up."""
        logger.info('initialize storage service')
        try:
            # We keep these tries short, since start-up connection problems
            # usually clear out pretty fast.
            if self.is_available(retries=20, connect_timeout=1,
                                 read_timeout=1):
                logger.info('storage service is already available')
                return
        except NoSuchBucket:
            logger.info('bucket does not exist; creating')
            self._create_bucket(retries=5, read_timeout=5, connect_timeout=5)
            logger.info('wait for bucket to be available')
            self._wait_for_bucket(retries=5, delay=5)
            return
        raise RuntimeError('Failed to initialize storage service')

    def _create_bucket(self, retries: int = 2, read_timeout: int = 5,
                       connect_timeout: int = 5) -> None:
        """Create S3 bucket."""
        config = Config(retries={'max_attempts': retries},
                        read_timeout=read_timeout,
                        connect_timeout=connect_timeout)
        client = self._new_client(config=config)
        client.create_bucket(Bucket=self._bucket)

    @classmethod
    def init_app(cls, app: Flask) -> None:
        """Set defaults for required configuration parameters."""
        app.config.setdefault('AWS_REGION', 'us-east-1')
        app.config.setdefault('AWS_ACCESS_KEY_ID', None)
        app.config.setdefault('AWS_SECRET_ACCESS_KEY', None)
        app.config.setdefault('S3_ENDPOINT', None)
        app.config.setdefault('S3_VERIFY', True)
        app.config.setdefault('S3_BUCKET', 'submission-preview')

    @classmethod
    def get_session(cls) -> 'PreviewStore':
        """Create a new :class:`botocore.client.S3` session."""
        config = get_application_config()
        return cls(config['S3_BUCKET'],
                   config['S3_VERIFY'],
                   config['AWS_REGION'],
                   config['S3_ENDPOINT'],
                   config['AWS_ACCESS_KEY_ID'],
                   config['AWS_SECRET_ACCESS_KEY'])

    @classmethod
    def current_session(cls) -> 'PreviewStore':
        """Get the current store session for this application."""
        g = get_application_global()
        if g is None:
            return cls.get_session()
        if 'store' not in g:
            g.store = cls.get_session()
        store: PreviewStore = g.store
        return store

    def _key(self, source_id: str, checksum: str) -> str:
        return f'preview/{source_id}/{checksum}/{source_id}.pdf'

    def deposit(self, preview: Preview, overwrite: bool = False,
                checksum: Optional[str] = None) -> Preview:
        """
        Deposit the content of a preview.

        Parameters
        ----------
        preview : :class:`.Preview`
            The ``content`` member **must** be set.
        overwrite : bool
            If True (default is False), will overwrite an existing key.
            Otherwise, if the key already exists, will raise
            :class:`.PreviewAlreadyExists`.
        checksum : str or None
            If provided, the checksum of the transferred content is verified
            against this checksum. A :class:`.DepositFailed` exception is
            raised if this check does not pass.

        Returns
        -------
        :class:`.Preview`
            A fresh representation of ``preview``, with its ``metadata``
            member set.

        Raises
        ------
        :class:`.PreviewAlreadyExists`
            Raised if an attempt is made to write a preview, and ``overwrite``
            is False.
        :class:`.DepositFailed`
            Raised if the preview content could not be deposited.

        """
        if preview.content is None:
            logger.error('Content is missing')
            raise DepositFailed('Content is missing')

        if not overwrite:
            try:
                self.get_metadata(preview.source_id, preview.checksum)
                logger.error('Preview already exists: %s @ %s',
                             preview.source_id, preview.checksum)
                raise PreviewAlreadyExists('Preview content already exists')
            except DoesNotExist:
                pass
        key = self._key(preview.source_id, preview.checksum)
        monitor = StreamMonitor(preview.content.stream)
        try:
            self.client.upload_fileobj(monitor, self._bucket, key,
                                       Config=TransferConfig(io_chunksize=4096))
        except ClientError as exc:
            try:
                self._handle_client_error(exc)
            except RuntimeError as e:
                logger.error('An unexpected error occurred: %s', e)
                raise DepositFailed('Could not deposit preview') from e

        if checksum is not None and monitor.checksum != checksum:
            msg = ('Checksum validation failed. Expected'
                   f' `{checksum}`, got `{monitor.checksum}`')
            logger.error(msg)
            self.client.delete_object(Bucket=self._bucket, Key=key)
            raise DepositFailed(msg)

        return Preview(source_id=preview.source_id,
                       checksum=preview.checksum,
                       content=preview.content,
                       metadata=Metadata(
                           checksum=monitor.checksum,
                           added=datetime.now(UTC),
                           size_bytes=monitor.size_bytes))

    def get_metadata(self, source_id: str, checksum: str) -> Metadata:
        """
        Retrieve :class:`.Metadata` about a :class:`.Preview`.

        Parameters
        ----------
        source_id : str
            Identifier of the source package.
        checksum: str
            Checksum of the source package.

        Returns
        -------
        :class:`.Metadata`

        Raises
        ------
        :class:`.DoesNotExist`

        """
        key = self._key(source_id, checksum)
        try:
            resp: HeadResponse = self.client.head_object(
                Bucket=self._bucket,
                Key=key
            )
        except ClientError as e:
            self._handle_client_error(e)
        return Metadata(checksum=_hex_to_b64(resp['ETag'][1:-1]),
                        added=resp['LastModified'],
                        size_bytes=resp['ContentLength'])

    def get_preview_checksum(self, source_id: str, checksum: str) -> str:
        """Get the preview content checksum via HEAD request."""
        try:
            resp: HeadResponse = self.client.head_object(
                Bucket=self._bucket,
                Key=self._key(source_id, checksum)
            )
        except ClientError as e:
            self._handle_client_error(e)
        return _hex_to_b64(resp['ETag'][1:-1])

    def get_preview(self, source_id: str, checksum: str) -> Preview:
        """Get the preview including its content."""
        try:
            resp: GetResponse = self.client.get_object(
                Bucket=self._bucket,
                Key=self._key(source_id, checksum)
            )
        except ClientError as e:
            self._handle_client_error(e)
        return Preview(source_id=source_id,
                       checksum=checksum,
                       metadata=Metadata(
                           checksum=_hex_to_b64(resp['ETag'][1:-1]),
                           added=resp['LastModified'],
                           size_bytes=resp['ContentLength']
                        ),
                       content=Content(stream=resp['Body']))



def _hex_to_b64(etag: str) -> str:
    """Convert an hexdigest of an MD5 to a URL-safe base64-encoded digest."""
    return urlsafe_b64encode(binascii.unhexlify(etag)).decode('utf-8')
