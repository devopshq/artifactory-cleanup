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

# move to rules config parent directory
cd $( dirname $ARTIFACTORY_RULES_CONFIG)

DESTROY=""
if [[ -v "$ARTIFACTORY_DESTROY_ARTEFACTS" ]]; then
    DESTROY="--destroy"
fi

# execute artifactory cleanup
echo "artifactory-cleanup $DESTROY --user $ARTIFACTORY_USER --password $ARTIFACTORY_PASSWORD --artifactory-server $ARTIFACTORY_URL --config $( basename $ARTIFACTORY_RULES_CONFIG)"
artifactory-cleanup $DESTROY --user $ARTIFACTORY_USER --password $ARTIFACTORY_PASSWORD --artifactory-server $ARTIFACTORY_URL --config $( basename $ARTIFACTORY_RULES_CONFIG)