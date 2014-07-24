#!/bin/bash

# https://github.com/kbase/assembly/issues/49

source test_library.sh

function main()
{
    ./arast.t &> my-log
    
    summarize_test my-log
}

main
