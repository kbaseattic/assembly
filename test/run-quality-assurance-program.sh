#!/bin/bash

function print_environment()
{
    echo "Date: $(date)"
    echo "Directory: $(pwd)"
    echo "Kernel: $(uname -a)"
    echo "Memory: $(head -n1 /proc/meminfo)"
    echo "Processor: $(grep 'model name' /proc/cpuinfo | head -n1)"


    echo ""
}

function run_test_suite()
{
    local entry_point
    local bucket_name
    local log_file
    local s3_path
    local result
    local elapsed_time

    entry_point=$1
    bucket_name=$2
    test_name=$3

    #echo "DEBUG $(pwd)"

    log_file=$entry_point.txt

    #time (echo "This is a test" &> $log_file) &> $log_file.time
    time (./$entry_point &> $log_file) &> $log_file.time

    elapsed_time=$(grep real $log_file.time|awk '{print $2}')
    result=$(tail -n1 $log_file)

    s3_path="s3://$bucket_name/tests/$test_name"

    aws s3 cp $log_file $s3_path/$log_file &> $log_file.s3

    address="https://$bucket_name.s3.amazonaws.com/tests/$test_name/$log_file"

    echo "TestSuite: $entry_point Result: $result Time: $elapsed_time Log: $address"
}

function test_endpoint()
{
    local topic
    local bucket_name
    local test_name
    local test_suite
    local log_file
    local address
    local endpoint
    local subject
    local message
    local repository
    local branch
    local directory

    repository="https://github.com/kbase/assembly.git"

    endpoint=$1
    branch=$2
    directory=$3
    
    # go in the common test directory
    cd $directory

    export ARAST_URL=$endpoint
    test_name=$(date +%Y-%m-%d-%H:%M:%S)
    bucket_name="kbase-assembly-service"

    # create current test directory and go inside it
    mkdir -p $test_name
    cd $test_name

    log_file="main.txt"

    (
    print_environment

    echo "TestName: $test_name"
    echo "Directory: $(pwd)"
    echo "Repository: $repository"
    echo "Branch: $branch"
    echo "Service endpoint: $endpoint"

    echo ""

    # Clone repository and deploy
    (
    echo "Clone"
    git clone $repository
    cd assembly
    git checkout $branch

    make -f Makefile.standalone deploy DEPLOY_RUNTIME=/software/python/2.7.3-1/
    ) &> clone.txt

    cd assembly
    cd test

    echo "Git Commit: $(git log | head -n1|awk '{print $2}')"

    # set up the path
    export PATH=$directory/$test_name/assembly/deployment/bin:$PATH

    # run tests
    run_test_suite arast.t.sh $bucket_name $test_name

    #run_test_suite . mock.sh $bucket_name $
    # run_test_suite $test_name integration_test_1.sh $bucket_name
    # run_test_suite $test_name test_SRS213780.sh $bucket_name

    ) | tee $log_file

    s3_path="s3://$bucket_name/tests/$test_name"

    aws s3 cp $log_file $s3_path/$log_file

    address="https://$bucket_name.s3.amazonaws.com/tests/$test_name/$log_file"

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

    local production_branch="master"
    local development_branch="dev"

    local directory="/home/boisvert/stuff/assembly-service-tests"

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
        test_endpoint $prod_url $production_branch $directory

    elif test $operand = "dev"
    then
        test_endpoint $dev_url $development_branch $directory

    elif test $operand = "default"
    then
        test_endpoint $prod_url $production_branch $directory
        test_endpoint $dev_url $development_branch $directory

    else
        test_endpoint $operand $production_branch $directory
    fi
}

main $@
