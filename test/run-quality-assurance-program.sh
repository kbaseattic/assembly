#!/bin/bash

function print_environment()
{
    echo "Date: $(date)"
    echo "Directory: $(pwd)"
    echo "Kernel: $(uname -a)"
    echo "Memory: $(head -n1 /proc/meminfo)"
    echo "Processor: $(grep 'model name' /proc/cpuinfo | head -n1)"

    echo "Git Commit: $(git log | head -n1|awk '{print $2}')"

    echo "Service endpoint: $ARAST_URL"
    echo ""
}

function run_test_suite()
{
    local directory
    local entry_point
    local bucket_name
    local log_file
    local path
    local bucket
    local result
    local elapsed_time

    directory=$1
    entry_point=$2
    bucket_name=$3

    bucket="s3://$bucket_name"

    log_file=$directory/$entry_point.txt

    #time (echo "This is a test" &> $log_file) &> $log_file.time
    time (./$entry_point &> $log_file) &> $log_file.time

    elapsed_time=$(grep real $log_file.time|awk '{print $2}')
    result=$(tail -n1 $log_file)

    path=$log_file

    aws s3 cp $log_file $bucket/$path &> $log_file.s3

    address="https://$bucket_name.s3.amazonaws.com/$path"

    echo "TestSuite: $entry_point Result: $result Time: $elapsed_time Log: $address"
}

function test_endpoint()
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
    local endpoint
    local subject
    local message

    endpoint=$1
    echo "test_endpoint $endpoint"
    return
    
    export ARAST_URL=$endpoint
    prefix="tests"
    test_name=$(date +%Y-%m-%d-%H:%M:%S)
    bucket_name="kbase-assembly-service"
    bucket="s3://$bucket_name"

    mkdir -p $prefix/$test_name
    log_file=$prefix/$test_name/"main.txt"

    (
    print_environment

    run_test_suite $prefix/$test_name arast.t $bucket_name
    run_test_suite $prefix/$test_name integration_test_1.sh $bucket_name
    run_test_suite $prefix/$test_name test_SRS213780.sh $bucket_name

    ) | tee $log_file


    path=$log_file
    aws s3 cp $log_file $bucket/$path

    address="https://$bucket_name.s3.amazonaws.com/$path"

    topic="arn:aws:sns:us-east-1:584851907886:kbase-assembly-service"
    subject="[KBase] Assembly Service quality assurance results ($endpoint)"

    message="$(cat $log_file)

Quality assurance result is available at $address."

    aws sns publish --topic-arn $topic --subject "$subject" \
    --message "$message"
}

function main()
{
    local argc=$#
    local prod_url="http://kbase.us/services/assembly"
    local dev_url="140.221.84.203"

    # default : dev && prod
    # dev     : "140.221.84.203"
    # prod    : "http://kbase.us/services/assembly"
    # string  : use string as endpoint 

    if test $argc -eq 0
    then
	main "default"
	return
    fi

    local operand=$1
    if test $operand = "prod"
    then
	test_endpoint $prod_url
    elif test $operand = "dev"
    then
	test_endpoint $dev_url
    elif test $operand = "default"
    then
	test_endpoint $prod_url
	test_endpoint $dev_url
    else
	test_endpoint $operand
    fi
}

main $@
