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
arast stat

message "Tests Complete: PASSED"