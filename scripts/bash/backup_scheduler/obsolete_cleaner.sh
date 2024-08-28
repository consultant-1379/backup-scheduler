#!/bin/bash

##############################################################################
# COPYRIGHT Ericsson AB 2018
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

# This script intend to clean up old empty directories after BUR successfully
# backuped new directories to the cloud

if [ $# -eq 0 ] ; then
  echo "No arguments supplied
  Script took one argument - <customer_name>"
  exit 1
fi

BACKUPPATH=/data1/rpcbackups

cleandir() {
if [ ! -d ${CUSTOMERPATH} ] ; then
  echo "${CUSTOMERPATH} don't exist. Exiting..."
  exit 1
cd ${CUSTOMERPATH}
if [ ! ${PWD} == ${CUSTOMERPATH} ] ; then
  echo "Can't change to ${CUSTOMERPATH}. Exiting..."
  exit 1
fi

for DIRNAME in $(ls -t) ; do
  if [ $(find ${DIRNAME} -type f | wc -l) -eq 2 ] \
  && [ -f ${DIRNAME}/backup.metadata ] \
  && [ -f ${DIRNAME}/BACKUP_OK ] ; then
    echo "${DIRNAME} will be deleted"
    rm ${DIRNAME}/{backup.metadata,BACKUP_OK}
    /usr/gnu/bin/find ${DIRNAME} -empty -delete
    if [ -d ${DIRNAME} ] ; then
      echo "WARN: ${DIRNAME} is still here"
    fi
  else
    echo "${DIRNAME} will not be deleted"
  fi
done
}

case ${1} in
  -h|--help|--usage)
    echo "Script took one argument - 'Customer Name'
    Given argument is ${1}"
    exit 0
  ;;
  cellcom|CellComENM01)
    echo "Argument ${1} was provided.
    CUSTOMERPATH=${BACKUPPATH}/CellComENM01 will be used"
    CUSTOMERPATH=${BACKUPPATH}/CellComENM01
    cleandir
  ;;
  chariton|cvenm01)
    echo "Argument ${1} was provided.
    CUSTOMERPATH=${BACKUPPATH}/cvenm01 will be used"
    CUSTOMERPATH=${BACKUPPATH}/cvenm01
    cleandir
  ;;
  charter|CbrsENM01)
    echo "Argument ${1} was provided.
    CUSTOMERPATH=${BACKUPPATH}/CbrsENM01 will be used"
    CUSTOMERPATH=${BACKUPPATH}/CbrsENM01
    cleandir
  ;;
  comcast|TrialENM01)
    echo "Argument ${1} was provided.
    CUSTOMERPATH=${BACKUPPATH}/TrialENM01 will be used"
    CUSTOMERPATH=${BACKUPPATH}/TrialENM01
    cleandir
  ;;
  cww|cwwenm01)
    echo "Argument ${1} was provided.
    CUSTOMERPATH=${BACKUPPATH}/cwwenm01 will be used"
    CUSTOMERPATH=${BACKUPPATH}/cwwenm01
    cleandir
  ;;
  ekn|EKNENM01)
    echo "Argument ${1} was provided.
    CUSTOMERPATH=${BACKUPPATH}/EKNENM01 will be used"
    CUSTOMERPATH=${BACKUPPATH}/EKNENM01
    cleandir
  ;;
  ksw|kswenm01)
    echo "Argument ${1} was provided.
    CUSTOMERPATH=${BACKUPPATH}/kswenm01 will be used"
    CUSTOMERPATH=${BACKUPPATH}/kswenm01
    cleandir
  ;;
  sprint|BMASenm01)
    echo "Argument ${1} was provided.
    CUSTOMERPATH=${BACKUPPATH}/BMASenm01 will be used"
    CUSTOMERPATH=${BACKUPPATH}/BMASenm01
    cleandir
  ;;
  staging01|staging01)
    echo "Argument ${1} was provided.
    CUSTOMERPATH=${BACKUPPATH}/staging01 will be used"
    CUSTOMERPATH=${BACKUPPATH}/staging01
    cleandir
  ;;
  staging05|genie-pipeline)
    echo "Argument ${1} was provided.
    CUSTOMERPATH=${BACKUPPATH}/genie-pipeline will be used"
    CUSTOMERPATH=${BACKUPPATH}/genie-pipeline
    cleandir
  ;;
  verizon|vzlabenm01)
    echo "Argument ${1} was provided.
    CUSTOMERPATH=${BACKUPPATH}/vzlabenm01 will be used"
    CUSTOMERPATH=${BACKUPPATH}/vzlabenm01
    cleandir
  ;;
  *)
    echo "Customer name you provided is not known.
    It will be used as directory name CUSTOMERPATH=${BACKUPPATH}/${1}"
    CUSTOMERPATH=${BACKUPPATH}/${1}
    cleandir
esac

