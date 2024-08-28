#!/usr/bin/env bash

DIR=$(dirname "$0")

function error {
    echo $@
    exit 10
}

[[ -z $CUSTOMER ]] && error CUSTOMER not defined
[[ -z $BACKUP_TAG ]] && error BACKUP_TAG not defined
[[ -z $BACKUP_ID ]] && error BACKUP_ID not defined

$DIR/run_backup_stages.py --customer=$CUSTOMER --stage=WAIT --nomail --tag=$BACKUP_TAG --id=$BACKUP_ID --stdout
