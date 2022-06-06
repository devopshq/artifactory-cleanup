#!/bin/bash

if [[ -z "$ARTIFACTORY_USER" ]];then
    echo "mandatory ARTIFACTORY_USER environment variable not set!"
    exit 3
fi
if [[ -z "$ARTIFACTORY_URL" ]];then
    echo "mandatory ARTIFACTORY_URL environment variable not set!"
    exit 3
fi
if [[ -z "$ARTIFACTORY_PASSWORD" ]];then
    echo "mandatory ARTIFACTORY_PASSWORD environment variable not set!"
    exit 3
fi
if [[ -z "$ARTIFACTORY_RULES_CONFIG" ]];then
    echo "mandatory ARTIFACTORY_RULES_CONFIG environment variable not set!"
    exit 3
fi

# check if /tmp/rules.py exists
[ ! -f "$ARTIFACTORY_RULES_CONFIG" ] && echo "$ARTIFACTORY_RULES_CONFIG not found" && exit 3

# install/trust self-signed certificates for Artifactory instances
# with self-signed CA
# further reading: https://askubuntu.com/a/649463
self_signed_certificates=$(shopt -s nullglob dotglob; echo /mnt/self-signed-certs/*)
if (( ${#self_signed_certificates} )); then
    cp /mnt/self-signed-certs/*.crt /usr/local/share/ca-certificates/
    update-ca-certificates
fi

# move to rules config parent directory
cd $( dirname $ARTIFACTORY_RULES_CONFIG)

DESTROY=""
if [[ -v ARTIFACTORY_DESTROY_MODE_ENABLED ]]; then
    DESTROY="--destroy"
fi

# execute artifactory cleanup
echo "artifactory-cleanup $DESTROY --user $ARTIFACTORY_USER --password $ARTIFACTORY_PASSWORD --artifactory-server $ARTIFACTORY_URL --config $( basename $ARTIFACTORY_RULES_CONFIG)"
artifactory-cleanup $DESTROY --user $ARTIFACTORY_USER --password $ARTIFACTORY_PASSWORD --artifactory-server $ARTIFACTORY_URL --config $( basename $ARTIFACTORY_RULES_CONFIG)