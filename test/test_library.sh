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
    local passed_ok
    local failed_ok
    local passed_all
    local failed_all
    local total
    local log_file
   
    log_file=$1

    passed=$(grep PASSED $log_file | wc -l)
    failed=$(grep FAILED $log_file | wc -l)

    passed_ok=$(grep "^ok" $log_file | wc -l)
    failed_ok=$(grep "^not ok" $log_file | wc -l)

    passed_all=$(($passed + $passed_ok))
    failed_all=$(($failed + $failed_ok))

    total=$(($passed_all + $failed_all))

    cat $log_file

    echo -n "PASSED: $passed_all/$total"

    if test $failed_all -ne 0
    then 
        echo -n " FAILED: $failed_all/$total"
    fi

    echo ""
}
