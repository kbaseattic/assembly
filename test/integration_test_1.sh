#!/bin/bash

# https://github.com/kbase/assembly/issues/49

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

function main()
{
    local file1
    local file2
    local server

    file1="ftp://ftp.ddbj.nig.ac.jp/ddbj_database/dra/fastq/SRA039/SRA039773/SRX081671/SRR306102_1.fastq.bz2"
    file2="ftp://ftp.ddbj.nig.ac.jp/ddbj_database/dra/fastq/SRA039/SRA039773/SRX081671/SRR306102_2.fastq.bz2"

    download $file1
    download $file2

    # don't use ar-upload because it is broken
    echo arast upload -m "SRS213780" --pair $(basename $file1) $(basename $file2) ARAST_URL=$server
    arast upload -m "SRS213780" --pair $(basename $file1) $(basename $file2)
}

main
