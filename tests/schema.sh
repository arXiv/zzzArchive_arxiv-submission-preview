#!/bin/bash

set -e

SCHEMA=$1

if [ -z ${MIN_SCORE} ]; then MIN_SCORE="9"; fi
pipenv run openapi-spec-validator ${SCHEMA}
SCHEMA_STATUS=$?
if [ $SCHEMA_STATUS -ne 0 ]; then SCHEMA_STATE="failure" && echo "openapi spec validation failed"; else SCHEMA_STATE="success" &&  echo "openapi spec validation passed"; fi
if [ "$TRAVIS_PULL_REQUEST_SHA" = "" ];  then SHA=$TRAVIS_COMMIT; else SHA=$TRAVIS_PULL_REQUEST_SHA; fi

if [ -z ${GITHUB_TOKEN} ]; then
    echo "Github token not set; will not report results";
else
    curl -u $USERNAME:$GITHUB_TOKEN \
        -d '{"state": "'$SCHEMA_STATE'", "target_url": "https://travis-ci.org/'$TRAVIS_REPO_SLUG'/builds/'$TRAVIS_BUILD_ID'", "context": "code-quality/openapi"}' \
        -XPOST https://api.github.com/repos/$TRAVIS_REPO_SLUG/statuses/$SHA \
        > /dev/null 2>&1;
fi