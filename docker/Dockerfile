FROM python:3.9.22-slim-bookworm

# set CERT paths for python libraries, necessary for self-signed certificates
#  - Requests Library
#  -> https://docs.python-requests.org/en/master/user/advanced/#ssl-cert-verification
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
#  - openssl
#  -> https://www.openssl.org/docs/man1.1.1/man3/SSL_CTX_set_default_verify_paths.html
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

COPY . /src
COPY docker/run.sh /opt/docker/run.sh

RUN pip install /src && rm -rf /src
WORKDIR /app

ENTRYPOINT ["bash", "/opt/docker/run.sh"]
