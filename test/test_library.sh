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
