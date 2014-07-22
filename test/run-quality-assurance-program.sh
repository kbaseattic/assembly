#!/bin/bash

function print_environment()
{
    echo "Git Commit: $(git log | head -n1|awk '{print $2}')"

}

function run_test_suite()
{
    local directory
    local entry_point
    local bucket_name
    local log_file
    local path
    local bucket

    directory=$1
    entry_point=$2
    bucket_name=$3

    bucket="s3://$bucket_name"

    log_file=$directory/$entry_point.log

    echo "This is a test" > $log_file
    #./$entry_point &> $log_file 

    path=$log_file

    aws s3 cp $log_file $bucket/$path

    address="https://$bucket_name.s3.amazonaws.com/$path"

    echo "Test= $entry_point, Log= $address"
}

function main()
{
    local topic
    local bucket
    local bucket_name
    local test_name
    local test_suite
    local path
    local log_file
    local address
    local prefix

    prefix="tests"
    test_name=$(date +%Y-%m-%d-%H:%M:%S)
    bucket_name="kbase-assembly-service"
    bucket="s3://$bucket_name"

    mkdir -p $prefix/$test_name
    log_file="main.log"

    (
    print_environment

    run_test_suite $prefix/$test_name arast.t $bucket_name

    ) | tee $log_file


    path=$prefix/$test_name/$log_file
    aws s3 cp $log_file $bucket/$path

    address="https://$bucket_name.s3.amazonaws.com/$path"

    topic="arn:aws:sns:us-east-1:584851907886:kbase-assembly-service"

    aws sns publish --topic-arn $topic --subject "[SNS] KBase Assembly Service quality assurance results" \
    --message "Quality assurance result is available at $address"
}

main
