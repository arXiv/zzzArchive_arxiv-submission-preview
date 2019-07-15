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
import boto3