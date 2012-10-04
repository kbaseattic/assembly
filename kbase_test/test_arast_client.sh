#!/bin/bash

set -e

export ARASTURL=140.221.84.124
export PATH=/kb/deployment/bin:$PATH

TEST_DIR="test_${$}"

function message {
    echo
    echo
    echo
    echo
    echo "##########################"
    echo "#"
    echo "# $1"
    echo "#"
    echo "##########################"
    echo
    echo
    echo
    echo
}


message "Check queue status"
arast -s $ARASTURL stat

message "Download synthetic metagenome (200MB)"
rm -f smg.fa
# curl -OL http://www.mcs.anl.gov/~fangfang/test/smg.fa
wget http://www.mcs.anl.gov/~fangfang/test/smg.fa

message "Submit synthetic  metagenome for kiki assembly and bwa mapping validation"
arast -s $ARASTURL run -a kiki -f smg.fa --bwa

message "Check job status"
sleep 2
arast -s $ARASTURL stat
sleep 5

message "Check random data status"
arast -s $ARASTURL stat --data 1
sleep 5

message "Wait 60s for job to finish and download results"
sleep 90
arast -s $ARASTURL get

message "Tests Complete: PASSED"