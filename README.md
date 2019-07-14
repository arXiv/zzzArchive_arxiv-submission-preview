# arXiv submission preview service

Clearinghouse for PDFs used during the submission process.

## Requirements

1. Provide a ``preview`` resource via RESTful API, identified by an unique string key.
2. Supports the following semantics:

- GET ``preview/<key>`` - Returns a JSON document describing the preview (creation time, creator, format, checksum, etc).
- GET ``preview/<key>/content`` - Returns the preview content.
- PUT ``preview/<key>`` - Creates a new preview resource at the specified key. Body of the request should be the preview content, and headers should identify content type. Metadata for the resource are automatically created based on the authn context and resource content.



Constraints

1. Backed by key value store, e.g. S3. Metadata should be stored alongside preview content.
