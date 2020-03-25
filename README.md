# arXiv submission preview service

Clearinghouse for PDFs used during the submission process.

## Requirements

1. Provide a ``preview`` resource via RESTful API. Resources should be identified by the source package ID and an URL-safe base64-encoded md5 hash of the source package from which it was generated, because:

   - Consumers should be able to specifically request a preview associated with a specific state of a submission upload workspace.
   - Not using submission ID, because compilation is submission-agnostic.
   - Not introducing a new ID, because the checksum is sufficient to uniquely identify the resource, and it can be known a priori by a consumer that has worked with the source package.

2. The API must support the following semantics:

- GET ``preview/<source id>/<hash>`` - Returns a JSON document describing the preview (creation time, creator, format, etc).
- GET ``preview/<source id>/<hash>/content`` - Returns the content (e.g. as ``application/pdf``).
- PUT ``preview/<source id>/<hash>/content`` - Creates a new preview resource at the specified key.

  - The body of the request should be the preview content, and headers should identify content type.
  - Metadata for the resource are automatically created based on the authn context and resource content.
  - Returns ``201 Created`` upon successful persistence of the content and metadata.


## Constraints

1. Backed by key value store. The initial implementation should use AWS S3. Metadata should be stored alongside preview content, e.g. as a JSON document.
2. Implemented using Python 3.6.x/Flask >= 1.
3. Must implement the patterns/practices described in https://arxiv.github.io/arxiv-arxitecture/crosscutting/services.html


## Tooling

- Localstack (https://github.com/localstack/localstack) can be used to simulate S3.
- Boto3 (https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) should be used to implement the service module that persists preview content and metadata.
- Moto (https://github.com/spulec/moto) may be used to mock/fake S3 in tests.


## Running the submission preview service locally

```bash
cd /path/to/arxiv-submission-preview
docker-compose pull    # build the images
docker-compose up      # start the service group
```

Give it a few seconds; localstack needs to come up (provides a local S3), and
a bucket will be created.


### Authentication + Authorization

To use the API you will need an auth token with scopes ``preview:read`` and
``preview:create``. The easiest way to generate one of these is to use the
helper script
[here](https://github.com/arXiv/arxiv-auth/blob/develop/users/bin/generate-token).
Make sure that you use the same ``JWT_SECRET`` that is used in
``docker-compose.yml``.

```bash
JWT_SECRET=foosecret pipenv run python generate_token.py
```
You should pass this token as the value of the ``Authorization`` header in
all requests to the API. For example:

```bash
curl -XPUT -H "Authorization: [auth token]" http://127.0.0.1:8000/...
```

### Creating preview data

This will create empty content:
```bash
curl -XPUT -H "Authorization: [auth token]" http://127.0.0.1:8000/12345/bar==/content
{"added":"2020-03-25T03:14:43.540174+00:00","checksum":"1B2M2Y8AsgTpgAmY7PhCfg==","size_bytes":0}
```

### Checking the submission preview status endpoint

You can request the status endpoint like this:
```bash
curl http://127.0.0.1:8000/status
{"iam":"ok"}
```
