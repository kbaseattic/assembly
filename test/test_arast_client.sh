#!/bin/bash

set -e

# export ARASTURL=140.221.84.124
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


message "Login with Tester's ID"
ar-login

message "Check queue status"
# arast -s $ARASTURL stat
ar-stat

mkdir -p tmpdir
cd tmpdir

message "Download synthetic metagenome (200MB)"
rm -f smg.fa
# curl -OL http://www.mcs.anl.gov/~fangfang/test/smg.fa
wget http://www.mcs.anl.gov/~fangfang/test/smg.fa

message "Submit synthetic  metagenome for kiki assembly"
export jobid=`ar-run -a kiki -f smg.fa`
echo "Job id = $jobid"

message "Check job status"
sleep 2
ar-stat
sleep 5

message "Wait 90s for job to finish and download results"
sleep 90

message "Check job status again"
sleep 2
ar-stat
sleep 3

ar-get -j $jobid

message "Tests Complete: PASSED"
