FROM python:3.13.7-alpine
ARG VERSION

WORKDIR .
COPY dist/pyatv-${VERSION}-py3-none-any.whl .
COPY requirements/requirements.txt .

RUN apk add gcc musl-dev build-base linux-headers libffi-dev rust cargo openssl-dev git && \
    pip install setuptools-rust && \
    pip install -r requirements.txt && \
    pip install pyatv-${VERSION}-py3-none-any.whl && \
    apk del gcc musl-dev build-base linux-headers libffi-dev rust cargo openssl-dev git && \
    rm pyatv-${VERSION}-py3-none-any.whl && \
    rm requirements.txt && \
    rm -rf /root/.cache /root/.cargo
