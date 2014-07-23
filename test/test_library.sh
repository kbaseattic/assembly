#!/bin/bash

function test_file()
{
    local file

    file=$1

    if test -f $file
    then
        echo "Test: test_file Object: $file Result: PASSED"
    else
        echo "Test: test_file Object: $file Result: FAILED"
    fi
}

function download()
{
    local file;

    file=$1

    name=$(basename $file)

    if ! test -f $name
    then
        wget $file
    fi

    test_file $name
}

function summarize_test()
{
    local passed
    local failed
    local total
    local log_file
   
    log_file=$1

    passed=$(grep PASSED $log_file | wc -l)
    failed=$(grep FAILED $log_file | wc -l)
    total=$(($passed + $failed))

    cat $log_file
    echo -n "PASSED: $passed/$total"
    if test $failed -ne 0
    then 
	 echo -n " FAILED: $failed/$total"
    fi
    echo ""
}
