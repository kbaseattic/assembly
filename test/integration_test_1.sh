#!/bin/bash

# https://github.com/kbase/assembly/issues/49

source test_library.sh

function download()
{
    local file;

    file=$1

    name=$(basename $file)

    if ! test -f $name
    then
        wget $file
    fi
}

function run_test()
{
    local file1
    local file2
    local server
    local file1_name
    local file2_name

    file1="ftp://ftp.ddbj.nig.ac.jp/ddbj_database/dra/fastq/SRA039/SRA039773/SRX081671/SRR306102_1.fastq.bz2"
    file2="ftp://ftp.ddbj.nig.ac.jp/ddbj_database/dra/fastq/SRA039/SRA039773/SRX081671/SRR306102_2.fastq.bz2"

    download $file1
    download $file2

    file1_name=$(basename $file1)
    file2_name=$(basename $file2)

    test_file $file1_name
    test_file $file2_name

    # don't use ar-upload because it is broken
    echo arast upload -m "SRS213780" --pair $file1_name $file2_name ARAST_URL=$server

    arast upload -m "SRS213780" --pair $file1_name $file2_name
}

function main()
{
    local passed
    local failed
    local total

    run_test &> my-log
    
    passed=$(grep PASSED my-log | wc -l)
    failed=$(grep FAILED my-log | wc -l)
    total=$(($passed + $failed))

    cat my-log

    echo "PASSED: $passed/$total FAILED: $failed/$total"
}

main
