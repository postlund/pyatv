FROM python:3.9.7-alpine
ARG VERSION

WORKDIR .
COPY dist/pyatv-${VERSION}-py3-none-any.whl .

RUN apk add gcc musl-dev build-base linux-headers libffi-dev rust cargo openssl-dev git && \
    pip install setuptools-rust && \
    pip install pyatv-${VERSION}-py3-none-any.whl && \
    apk del gcc musl-dev build-base linux-headers libffi-dev rust cargo openssl-dev git && \
    rm pyatv-${VERSION}-py3-none-any.whl && \
    rm -rf /root/.cache /root/.cargo
