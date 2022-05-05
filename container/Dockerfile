FROM python:3.9.12-slim-buster
ARG VERSION

WORKDIR /app

COPY customrun.sh .

COPY certificates/*.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates

# set CERT paths
#  - Requests Library
ENV REQUESTS_CA_BUNDLE /etc/ssl/certs/ca-certificates.crt 
#  - openssl
ENV SSL_CERT_FILE /etc/ssl/certs/ca-certificates.crt

RUN pip install artifactory-cleanup==${VERSION}

CMD ["bash", "customrun.sh"]