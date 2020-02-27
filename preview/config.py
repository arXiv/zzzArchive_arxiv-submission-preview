"""Application configuration for submission preview service."""

from os import environ

APP_VERSION = "0.1rc1"

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

WAIT_FOR_SERVICES = bool(int(environ.get('WAIT_FOR_SERVICES', '1')))
"""Whether or not to wait for upstream services before starting."""

# --- VAULT INTEGRATION CONFIGURATION ---

VAULT_ENABLED = bool(int(environ.get('VAULT_ENABLED', '0')))
"""Enable/disable secret retrieval from Vault."""

KUBE_TOKEN = environ.get('KUBE_TOKEN', 'fookubetoken')
"""Service account token for authenticating with Vault. May be a file path."""

VAULT_HOST = environ.get('VAULT_HOST', 'foovaulthost')
"""Vault hostname/address."""

VAULT_PORT = environ.get('VAULT_PORT', '1234')
"""Vault API port."""

VAULT_ROLE = environ.get('VAULT_ROLE', 'submission-ui')
"""Vault role linked to this application's service account."""

VAULT_CERT = environ.get('VAULT_CERT')
"""Path to CA certificate for TLS verification when talking to Vault."""

VAULT_SCHEME = environ.get('VAULT_SCHEME', 'https')
"""Default is ``https``."""

VAULT_REQUESTS = [
    {'type': 'generic',
     'name': 'JWT_SECRET',
     'mount_point': f'secret{NS_AFFIX}/',
     'path': 'jwt',
     'key': 'jwt-secret',
     'minimum_ttl': 3600},
    {'type': 'aws',
     'name': 'AWS_S3_CREDENTIAL',
     'mount_point': f'aws{NS_AFFIX}/',
     'role': environ.get('VAULT_CREDENTIAL')},
]
"""Requests for Vault secrets."""
