#!/usr/bin/env bash


LOGDIR=$1
[[ -z $LOGDIR ]] && exit 1

cd $LOGDIR


for logfile in *log ; do
    fuser $logfile &> /dev/null && continue
    test -s $logfile || continue
    mv ${logfile}.2 ${logfile}.3 &>/dev/null
    mv ${logfile}.1 ${logfile}.2 &>/dev/null
    mv ${logfile} ${logfile}.1 &>/dev/null
    touch $logfile
done

