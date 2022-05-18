FROM python:3.9.12-slim-buster

COPY . /app
WORKDIR /app

# set CERT paths for python libraries, necessary for self-signed certificates
#  - Requests Library
#  -> https://docs.python-requests.org/en/master/user/advanced/#ssl-cert-verification
ENV REQUESTS_CA_BUNDLE /etc/ssl/certs/ca-certificates.crt
#  - openssl
#  -> https://www.openssl.org/docs/man1.1.1/man3/SSL_CTX_set_default_verify_paths.html
ENV SSL_CERT_FILE /etc/ssl/certs/ca-certificates.crt

RUN pip install .

CMD ["bash", "/app/docker/run.sh"]
