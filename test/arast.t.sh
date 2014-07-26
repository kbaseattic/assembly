#!/bin/bash

# https://github.com/kbase/assembly/issues/49

source test_library.sh

function main()
{
    local log_file

    log_file=$(mktemp)

    ./arast.t &> $log_file
    
    summarize_test $log_file

    rm $log_file
}

main
