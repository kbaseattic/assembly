#!/usr/bin/env ruby

# https://github.com/kbase/assembly/issues/49

def download file
    name = file.split('/').last

    unless File.exists? name
        Kernel.system("wget " + file)
    end
end

download "ftp://ftp.ddbj.nig.ac.jp/ddbj_database/dra/fastq/SRA039/SRA039773/SRX081671/SRR306102_1.fastq.bz2"
download "ftp://ftp.ddbj.nig.ac.jp/ddbj_database/dra/fastq/SRA039/SRA039773/SRX081671/SRR306102_2.fastq.bz2"


