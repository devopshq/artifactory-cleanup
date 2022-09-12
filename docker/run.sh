#!/bin/bash
# install/trust self-signed certificates for Artifactory instances
# with self-signed CA
# further reading: https://askubuntu.com/a/649463
self_signed_certificates=$(shopt -s nullglob dotglob; echo /mnt/self-signed-certs/*)
if (( ${#self_signed_certificates} )); then
    cp /mnt/self-signed-certs/*.crt /usr/local/share/ca-certificates/
    update-ca-certificates
fi

echo "Command to execute: $*"
exec "$@"
