ARG BASE_VERSION=latest

FROM arxiv/base:${BASE_VERSION}

WORKDIR /opt/arxiv/

COPY wsgi.py uwsgi.ini Pipfile Pipfile.lock /opt/arxiv/
RUN pipenv install && rm -rf ~/.cache/pip

ENV PATH="/opt/arxiv:${PATH}" \
    LC_ALL="en_US.utf8" \
    LANG="en_US.utf8" \
    LOGLEVEL=40 \
    APPLICATION_ROOT="/"

EXPOSE 8000

COPY preview /opt/arxiv/preview

ENTRYPOINT ["pipenv", "run"]
CMD ["uwsgi", "--ini", "/opt/arxiv/uwsgi.ini"]
