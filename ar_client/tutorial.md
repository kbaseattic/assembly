Using the Assembly Service Command-Line Client
=============================================

Introduction
------------
The DOE KBase features an Assembly Service with tools that allow users to submit a variety of sequence datasets to be processed, assembled, and analyzed.  This tutorial will introduce you to the current capabilities of the service as well as give some command-line recipes.

Currently at an early phase, the Assembly Service has the following computation capabilities:

* Velvet assembly
* Kiki assembly
* BWA alignment

Installation
------------
### Prerequisites ###
* Python easy_install module

### Prepackaged Installation in Unix ###
The Assembly Service Client uses Python's Easy Install module to manage and install dependencies.  To install, first download the latest .egg package from the [KBase Downloads page](http://kbase.us/index.php/developers/downloads/).  To install:

`sudo easy_install ar_client-<VERSION>.egg`

Running the Service
-------------------
We will walk through building a command-line recipe depending on desired options.  First, running an assemblies is performed via the `run` subcommand:

`arast run ...`

NOTE: The default behavior of the client is to use the official KBase Assembly Server.  To invoke the client against an alternate server, use the `-s` flag:

`arast -s SERVER run ...`

### Sequence Data ###
We can submit data in multiple fashions:

`arast run -f READS1.fa READS2.fa ...`
`arast run -f /path/to/sequences/ ...`

#### Previously submitted datasets: `--data` ####

`arast run --data DATAID ...`

\(We will explain DATAID later in the tutorial\)

### Assemblers ###
The Assembly service is designed to be flexible and extensible to offer multiple assembler options.  Currently, the assembler choices are:

* `kiki`
* `velvet`

Thus, to run an assembly:

`arast run -f READS.fa -a kiki [...]`

or multiple assemblies:

`arast run -f READS.fa -a kiki velvet [...]`

### Processing / Analysis ###
The Assembly service currently offers the current processing services:

#### BWA: `--bwa` ####

Using this option will invoke a BWA alignment which queries the initial reads against the assembled contig\(s\).

`arast run -f READS.fa -a kiki --bwa`

### Other Options ###
#### User Comments/Description ####
The user can submit a description with the job for personal bookkeeping:

`arast run -f READS.fa -a kiki -m "My description"`

Job / Data Status
-----------------

### Job Status ###
Checking the status of job and data submissions is performed via the `stat` sub-command.  To check the status of the most recent jobs:

`arast stat [...]`

or the status of any number of previous jobs:

`arast stat -n NUM [...]`


### Dataset information ###

The returned output gives the user information about submitted jobs:

    +--------+---------+----------+----------+-------------+
    | Job ID | Data ID |  Status  | Run time | Description |
    +--------+---------+----------+----------+-------------+
    |   42   |    17   | complete | 0:00:16  |    test3    |
    +--------+---------+----------+----------+-------------+

Here, we can see the "Data ID" of the specific dataset.  With this, we can attain information about it:

`arast stat --data 17`

which will output

    +---+--------+-----------+
    | # |  File  |    Size   |
    +---+--------+-----------+
    | 1 | sm1.fa | 203372422 |
    | 2 | sm2.fa | 534524543 |
    +---+--------+-----------+

Retrieving Results
------------------
Once it is confirmed that a job's "Status" is "complete," result data can be downloaded from the server.  To download result data from a completed job:

`arast get -j JOB_ID`

