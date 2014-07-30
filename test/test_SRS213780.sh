#!/bin/bash

# https://github.com/kbase/assembly/issues/49

source test_library.sh

function run_test()
{
    local file1
    local file2
    local file1_name
    local file2_name
    local data_identifier
    local job_identifier
    local job_status

    file1="ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR306/SRR306102/SRR306102_1.fastq.gz"
    file2="ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR306/SRR306102/SRR306102_2.fastq.gz"

    download $file1
    download $file2

    file1_name=$(basename $file1)
    file2_name=$(basename $file2)

    test_file $file1_name
    test_file $file2_name

    arast upload -m "test_SRS213780.sh" --pair $file1_name $file2_name > data.txt

    test_file data.txt

    data_identifier=$(cat data.txt | awk '{print $3}')

    arast run --data $data_identifier > job-identifier.txt

    test_file job-identifier.txt

    job_identifier=$(cat job-identifier.txt | awk '{print $3}')

    job_status="state-zero"

    while true
    do
        sleep 5
        echo "DEBUG sleep 5"
        job_status=$(arast stat -j $job_identifier | awk '{print $1}')

        if test $job_status = "Complete"
        then
            break
        fi
        if test $job_status = "[FAIL]"
        then
            break
        fi
        if test $job_status = "Terminated"
        then
            break
        fi
    done
}

function main()
{
    run_test &> my-log

    summarize_test my-log
}

main
