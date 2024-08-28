#!/usr/bin/env bash

DIR=$(dirname "$0")

function error {
    echo $@
    exit 10
}

[[ -z ${CUSTOMER} ]] && echo "error CUSTOMER not defined"

OUT=$( $DIR/run_backup_stages.py --customer=$CUSTOMER --stage=BACKUP --nomail --stdout )
RET=$?
INFO=$(grep ^ID <<< "$OUT" )
ID=$(awk ' { print $2 } ' <<<$INFO) 
TAG=$(awk ' { print $4 } ' <<<$INFO)

echo "BACKUP_ID=$ID" >> out.properties
echo "BACKUP_TAG=$TAG" >> out.properties

echo "$OUT"
exit $RET
