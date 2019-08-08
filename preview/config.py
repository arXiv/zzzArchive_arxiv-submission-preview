"""Application configuration for submission preview service."""

from os import environ

APP_VERSION = "0.0"

NAMESPACE = environ.get('NAMESPACE')
"""Namespace in which this service is deployed; to qualify keys for secrets."""

DEBUG = environ.get('DEBUG') == '1'
"""enable/disable debug mode"""

SERVER_NAME = environ.get('SERVER_NAME', None)

APPLICATION_ROOT = environ.get('APPLICATION_ROOT', '/')

JWT_SECRET = environ.get('JWT_SECRET', 'foosecret')
"""Secret key for auth tokens."""

NS_AFFIX = '' if NAMESPACE == 'production' else f'-{NAMESPACE}'

S3_BUCKET = environ.get('S3_BUCKET', f'preview{NS_AFFIX}')
S3_VERIFY = bool(int(environ.get('S3_VERIFY', '1')))
S3_ENDPOINT = environ.get('S3_ENDPOINT', None)
AWS_REGION = environ.get('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY_ID = environ.get('AWS_ACCESS_KEY_ID', 'fookey')
AWS_SECRET_ACCESS_KEY = environ.get('AWS_SECRET_ACCESS_KEY', 'foosecret')

MAX_PAYLOAD_SIZE_BYTES = 100 * 1_028
