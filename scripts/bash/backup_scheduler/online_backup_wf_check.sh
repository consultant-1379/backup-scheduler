#!/usr/bin/env bash

DIR=$(dirname "$0")

function error {
    echo $@
    exit 10
}

[[ -z $CUSTOMER ]] && error CUSTOMER not defined

$DIR/run_backup_stages.py --customer=$CUSTOMER --stage=WFS --nomail --stdout
