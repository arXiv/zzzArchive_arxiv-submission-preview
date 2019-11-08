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
