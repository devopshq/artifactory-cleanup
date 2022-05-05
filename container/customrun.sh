#!/bin/bash

if [[ -z "$ARTI_USER" ]];then
    echo "mandatory ARTI_USER environment variable not set!"
    exit 3
fi
if [[ -z "$ARTI_URL" ]];then
    echo "mandatory ARTI_URL environment variable not set!"
    exit 3
fi
if [[ -z "$ARTI_PW" ]];then
    echo "mandatory ARTI_PW environment variable not set!"
    exit 3
fi
if [[ -z "$RULES_CONFIG" ]];then
    echo "mandatory RULES_CONFIG environment variable not set!"
    exit 3
fi

# check if /tmp/rules.py exists
[ ! -f "$RULES_CONFIG" ] && echo "$RULES_CONFIG not found" && exit 3

# move to rules config parent directory
cd $( dirname $RULES_CONFIG)

DRY_RUN=""
if [[ -v DISABLE_DRY_RUN ]]; then
    DRY_RUN="--destroy"
fi

# execute artifactory cleanup
echo "artifactory-cleanup $DRY_RUN --user $ARTI_USER --password $ARTI_PW --artifactory-server $ARTI_URL --config $( basename $RULES_CONFIG)"
artifactory-cleanup $DRY_RUN --user $ARTI_USER --password $ARTI_PW --artifactory-server $ARTI_URL --config $( basename $RULES_CONFIG)