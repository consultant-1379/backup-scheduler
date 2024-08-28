#!/usr/bin/env bash

DIR=$(dirname "$0")

function error {
    echo $@
    exit 10
}


[[ -z $CUSTOMER ]] && error CUSTOMER not defined

$DIR/set_customer_retention.py --customer=$CUSTOMER --retention=$RETENTION_VALUE --stdout

