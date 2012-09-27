Assembly Service Commandline Client
==================================

Installation
------------
`sudo easy_install EGG_FILE`


Statistics
----------
View jobs list

`arast stat`

Monitor jobs list in realtime

`arast stat -w`

View files of known data id

`arast stat --files 39`


Running jobs
------------
Run assemblies on specific files

`arast run -f reads1.fa reads2.fa -a kiki velvet -m "My job description"`

Run assemblies on all files in directory

`arast run -d dir_of_reads/ -a kiki velvet -m "My job description"`

Run assemblies on previously uploaded data

`arast run --data 42 -a kiki velvet -m "My job description"`


Downloading results
-------------------
Download latest job results

`arast get`

Download JOB_ID results

`arast get -j 42`