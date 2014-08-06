# Using the Assembly Service Commands

## Introduction 

The Assembly Service is a web-based environment that allows users to
submit datasets of sequence reads to be processed, assembled, and
analyzed.  This tutorial will introduce you to the current
capabilities of the service as well as giving some command-line
recipes. You will learn how to upload a set of read files, assemble
them, inspect the results, and select the best assembly for your
downstream analysis.

We believe the default pipeline performs well. However, we encourage
you to experiment with alternative assemblers, preprocessing tools,
and parameter settings. Our service currently supports over 20
assemblers and tools, and its modular design allows for
straightforward extension as sequencing technologies and analysis
tools evolve. We have also built a pipeline engine that allows you to
mix and match approaches and evaluate a variety of customized
pipelines on your datasets.

We will start with a very simple example. Then, we will step through
the commands and options. Since a thorough assembly on a microbial
genome can take hours, we will use a partial dataset in the early
examples for quick turnaround. In the final set of examples, we will
work with some real data. This tutorial will focus on microbial
assembly, although some of the modules included in the service
supports assembly of low-complexity metagenomes.

## A Simple Example

The following command will instruct the server to assemble a file of
single-end reads specified by the URL using the velvet assembler. This
should take just a couple minutes.

```inv
ar-run -a velvet --single_url http://www.mcs.anl.gov/~fangfang/arast/se.fastq | ar-get --wait --pick > ex1.contigs.fasta
```

This command will block until the assembly is done. The resulting set
of contigs will be saved to a FASTA file local to the client. The
choice of output name is arbitrary; we use `ex1.contigs.fasta` to
denote it's the contigs from our first exercise. You can use the Unix
`cat` utility to inspect the content of the contig file.

```inv
cat ex1.contigs.fasta
```
```out
>NODE_1_length_56_cov_204.767853
TACTAAAATTATAATTTTCCTGATTTTTGTAGAGGAGTATGGGAAAGTTCTGTGTATTTT
ATGCTTTTATCCGTATTTAGGAGT
>NODE_2_length_81_cov_258.320984
TTTTATGCTTTTATCCGTATTTAGGAGTTAGAGGCTAGAGATGATGGAGTAAATTGTAAA
ATCAGGCTAGTGAAGGATCTGAATATCCATTTCTATTTACCTGAAATAT
>NODE_3_length_1762_cov_171.553909
AATCAACGAAGCAGGAGCATACTGGTAAGCGACAGTTAAAAGGAAGTATGCAATATTTAT
TATTACTCCTAACAGCGCTATCAAGCTAAAGTCCTTCAAGTTAGGAAAAGATCCTTCCCA
...
```

The one-liner command above uses two operators on Unix-like systems: the
pipe operator `|` for chaining commands, and the redirection operator
`>` to save output normally directed to the screen to a designated
file. They are used here for convenience and are not necessary in the
step-by-step way of using the assembly service.


## Getting Started

The commands and options we describe in this tutorial are supported on
the clients of version 0.5.1 or newer. To check your client version, type:

```inv
ar-stat --version
```
```out
AssemblyRAST Client 0.5.3
```

Here is the list of client commands. You can use the "-h" option to
consult the usage information for each command.
```
ar-login, ar-logout, ar-upload, ar-run, ar-stat, ar-get, ar-filter, ar-kill, ar-avail
```

### Authentication

If you are using one of the browser-based clients, you may have
already signed in using the widget located on the upper-right corner
of your window. If you are using the command-line client from the
terminal, you can type the following commands to authenticate, or
switch to a different account.

```
ar-login
ar-logout
```

### Submitting a set of read files

An input dataset for assembly is usually composed of one or multiple
single-end libraries or paired-end libraries in the FASTQ format. You
can define your data object and submit it to the assembly server using
the `ar-upload` command with a combination of `--single` and `--pair`
options. You can use either option more than once for multiple
libraries of the same type.

To illustrate this, you can first download two small files we have
prepared to your client local space.

```bash
curl http://www.mcs.anl.gov/~fangfang/arast/b99_1.fq > p1.fq
curl http://www.mcs.anl.gov/~fangfang/arast/b99_2.fq > p2.fq
```

You can of course skip the above step and submit your own
files. Here's an example of the upload command, assuming you already
have two local sequence files named `p1.fq` and `p2.fq`:

```inv
ar-upload --pair p1.fq p2.fq > ex2.data_id
```
The upload will return a data ID from the server. The data ID allows
you to invoke different assemblers or pipelines on the same data
without resubmitting it. In the example above, we used the
`> ex2.data_id` redirection to save the data ID to a file. If you omit
that part, an integer ID will be printed to the screen upon successful
submission:
```
Data ID: 155
```


### Launching an assembly job

To launch our default assembly pipeline on the dataset you submitted
in the previous section, you can simply type:

```inv
cat ex2.data_id | ar-run > ex3.job_id
```

If you don't have the data ID saved in a file, you can instead type
something such as `ar-run --data 115`.

Note that the assembly job is asynchrnous. The `ar-run` command should
return immediately with a job ID (e.g., `Job ID: 223`) with which you
can query the job status.

As we have shown in our first exercise, you can also bypass the
`ar-upload` step and launch a job directly. Here is an example.

```inv
ar-run --pair p1.fq p2.fq -p tagdust idba -m "my test job"
```

This command should return as soon as the data is uploaded. Note that we
are also explicitly invoking the `tagdust` preprocessing module and
the `idba` assembler using the `-p` pipeline option. You can use the
`ar-avail` command to list all the modules supported. We will describe
those and the pipeline support in the Advanced Features section.

Both the `ar-run` and `ar-upload` commands allow you to specify a
reference genome with the `--reference genome.fasta` option. It can
be used to score the assemblies in the evaluation step. 


### Assemblers, pipelines, and recipes

There are three main options for defining an assembly job on your
dataset:

1. `-a assembler`:  invokes an individual assembler on raw reads.
2. `-p module1 module2 ... assembler`:  runs a pipeline of preprocessing and assembler modules
3. `-r recipe`:  uses a predefined pipeline which we call a "recipe"

You can combine `-a` and `-p` options but not the `-r` option. Here
are some valid option examples for `ar-run`:
```
-a velvet -a a6
-p bhammer spades -a ray -p kiki sspace
-r fast
```

We have curated a set of recipes that tend to work well for certain
datasets. You can list them using the `--recipe` option in the
ar-avail command:

```inv
ar-avail --recipe
```
```out
[Recipe] auto
  1. Runs BayesHammer on reads
  2. Assembles with Velvet, IDBA and SPAdes
  3. Sorts assemblies by ALE score

[Recipe] smart
  1. Runs BayesHammer on reads, Kmergenie to choose hash-length for Velvet
  2. Assembles with Velvet, IDBA and SPAdes
  3. Sorts assemblies by ALE score
  4. Merges the two best assemblies with GAM-NGS

[Recipe] fast
  Assembles with A6, Velvet and SPAdes (with BayesHammer for error correction).
  Results are sorted by N50 Score.

[Recipe] faster
  Assembles with A6 and Velvet.
  Results are sorted by N50 Score.
  Works well for some short read datasets.

...
```


### Job management

To monitor the job and data status, you can use variations of the
`ar-stat` command. To get the list of recently submitted jobs, type:

```inv
ar-stat
```
```out
+--------+---------+----------------------+----------+------------------+
| Job ID | Data ID |        Status        | Run time |   Description    |
+--------+---------+----------------------+----------+------------------+
|  133   |    58   |  [FAIL] Data Error   | 0:09:12  |       None       |
|  134   |    60   |       Complete       | 0:01:57  |   my test job    |
|  135   |    62   |       Complete       | 0:00:21  |       None       |
|  136   |    63   |       Complete       | 0:03:53  |       None       |
|  137   |    64   |       Complete       | 0:02:26  |       None       |
|  138   |    65   | Stage 2/9: kmergenie | 0:00:59  | default pipeline |
|  139   |    66   |  Stage 3/5: velvet   | 0:00:59  | parameter sweep  |
|  140   |    68   |   Stage 2/3: idba    | 0:00:59  |   my test job    |
|  141   |    70   |       Complete       | 0:00:21  |   RAST recipe    |
|  142   |    71   | Stage 2/5: kmergenie | 0:00:30  |   kmer tuning    |
+--------+---------+----------------------+----------+------------------+
```

When a job is in progress, its stage information is updated in the
Status field; otherwise, it can end in one of the following states:
"Complete", "Complete with error", "Terminated", and "FAIL [description]".
You can use the `ar-stat -j job_id` command to inspect the error
message for a failed job.

You may notice that of the two jobs we just launched, the second one
may finish first. That's because our default pipeline
invokes multiple assemblers on your dataset with parameter tuning. It
may even try to reconcile and merge the best individual assemblies.

The status table also gives you the data ID for each job. However, you
may need to list all the datasets you have uploaded but may not
necessarily have computed on. For that, you can type:

```inv
ar-stat -l
```
```out
+---------+--------------+---------------+-------------------------------+
| Data ID | Description  |      Type     |             Files             |
+---------+--------------+---------------+-------------------------------+
|   151   |     None     |               |                               |
|         |              |     paired    | p1.fq (39.8MB) p2.fq (39.8MB) |
|   152   |     None     |               |                               |
|         |              |   reference   |             ref.fa            |
|         |              |     paired    |          p2.fq p1.fq          |
|   153   |     None     |               |                               |
|         |              |   paired_url  |       b99_1.fq b99_2.fq       |
|   154   |     None     |               |                               |
|         |              |     paired    | p1.fq (39.8MB) p2.fq (39.8MB) |
|         |              | reference_url |           b99.ref.fa          |
|   155   | my test data |               |                               |
|         |              |     single    |             se.fq             |
|   156   |     None     |               |                               |
|         |              |   single_url  |            se.fastq           |
+---------+--------------+---------------+-------------------------------+
```

### Getting assembly results

Once a job completes, you can look at the report of assembly
statitistics and pick your best set of contigs. You can also choose to
download the whole data directory which includes detailed log files
and a visual comparison of all the assemblies.

Use `ar-get -j job_id --report` to show the text assembly report. You
can add the `--wait` option to make sure the command waits for the job
to complete. In the following example, we specify the job ID from a
file we have previously saved.

```inv
cat ex3.job_id | ar-get --report --wait
```
```out
QUAST: All statistics are based on contigs of size >= 500 bp, unless otherwise noted (e.g., "# contigs (>= 0 bp)" and "Total length (>= 0 bp)" include all contigs).

Assembly                        spades_contigs  gam_ngs_contigs  idba_contigs  velvet_contigs
# contigs (>= 0 bp)             3629            3543             3562          32840
# contigs (>= 1000 bp)          977             967              735           397
Total length (>= 0 bp)          3085770         3086007          2549247       3234730
Total length (>= 1000 bp)       1889425         1938839          1206779       665559
# contigs                       1947            1879             1780          902
Largest contig                  11126           11126            7592          8135
Total length                    2571219         2578689          1929576       1025928
Reference length                3084257         3084257          3084257       3084257
GC (%)                          56.51           56.51            55.99         55.20
Reference GC (%)                56.89           56.89            56.89         56.89
N50                             1585            1664             1212          1265
NG50                            1314            1397             723           -
...
```

You can pick an assembly using numeric or string IDs (e.g., `ar-get
--pick 1`, where 1 stands for the first assembly column, is equivalent
to `ar-get --pick spades` in the example above). By default,
the `--pick` option will select the best assembly based on a set of
common metrics.  We are actively working on improving the scoring
functions for reference-based and reference-free assemblies.

```inv
cat ex3.job_id | ar-get --wait --pick > ex4.contigs.fasta
```

You can also use the `ar-filter` command to keep only the contigs
satisfying certain length and coverage requirements. For example, if
you are only interested in using contigs longer than 500 bp and with
read coverage above 2.0 for your downstream analysis, you can type:

```inv
cat ex3.job_id | ar-get --wait --pick | ar-filter -l 500 -c 2.0 > ex4.filtered.contigs.fa
```

To download the whole assembly directory on the server, type:

```inv
cat ex3.job_id | ar-get -o ex5.dir
```

The directory `ex5.dir` will contain the report file, contig files,
and visualized analysis output:
```
ex5.dir/214_report.txt
ex5.dir/214_1.spades_contigs.fasta
ex5.dir/214_2.velvet_contigs.fa
ex5.dir/214_analysis/report.html
ex5.dir/214_analysis/report.pdf
...
```

Assembly pipelines can fail for a variety reasons. Some modules do not
support long reads or multiple libraries; others are simply not
robust. When an assembly job includes multiple pipelines, it will try
to skip the failed ones and only include the successful assemblies in
the final report. You can inspect the full pipeline logs with the
`ar-get --log` option.


## Advanced Features

### Modules

You can find the list of assemblers and supporting modules
available in the assembly service by typing:

```inv
ar-avail
```
```out
Module           Stages                              Description
----------------------------------------------------------------
a5               preprocess,assembler,post-process   A5 microbial assembly pipeline
a6               preprocess,assembler,post-process   Modified A5 microbial assembly pipeline
bhammer          preprocess                          SPAdes component for quality control of sequence data
bowtie2          post-process                        Bowtie2 aligner that maps reads to contigs
bwa              post-process                        BWA aligner that maps reads to contigs
fastqc           preprocess                          FastQC quality control tool for sequence data
filter_by_length preprocess                          Length-based sequencing reads filter and trimmer based on seqtk
idba             assembler                           IDBA iterative graph-based assembler for single-cell and standard data
kiki             assembler                           Kiki overlap-based parallel microbial and metagenomic assembler
quast            post-process                        QUAST assembly quality assessment tool (run by default)
ray              assembler                           Ray graph-based parallel microbial and metagenomic assembler
reapr            post-process                        REAPR assembly error recognizer using paired-end reads
sga_ec           preprocess                          SGA component for error correction (runs subcommands: 'index' & 'correct')
sga_preprocess   preprocess                          SGA component for preprocessing reads (runs subcommand 'preprocess')
spades           preprocess,assembler                SPAdes single-cell and standard assembler based on paired de Bruijn graphs
sspace           post-process                        SSPACE pre-assembled contig scaffolder
swap             assembler                           SWAP Assembler
tagdust          preprocess                          TagDust sequencing artifacts remover
trim_sort        preprocess                          DynamicTrim and LengthSort from SolexaQA
velvet           assembler                           Velvet de-bruijn graph based assembler
```

To see the details for each module including customizable parameters,
version and reference information, you can use the `--detail` option:

```inv
ar-avail --detail
```
```out
...
[Module] trim_sort
  Description: DynamicTrim and LengthSort from SolexaQA
  Version: 1.0
  Stages: preprocess
  References: doi:10.1186/1471-2105-11-485
  Customizable parameters: default (available values)
                   length  =  25
               probcutoff  =  0.05
											
[Module] velvet
  Description: Velvet de-bruijn graph based assembler
  Version: 1.0
  Base Version: 1.2.10
  Stages: assembler
  References: doi:10.1101/gr.074492.107
  Customizable parameters: default (available values)
              auto_insert  =  False
              hash_length  =  29
```

### Pipelines

You can mix and match different preprocessing modules and assemblers
to form multiple pipelines in one submission. For example, the
following command will launch four pipelines and compare the resulting
assemblies.

```inv
ar-run --pair pe1.fq pe2.fq -p 'none tagdust' 'velvet kiki'
```

The cartesian expansion of the pipeline expression generates four pipelines:
```
velvet
kiki
tagdust velvet
tagdust kiki
```

### Parameters

Some of the modules support customizable parameters. You can use them
to launch parameter sweep pipelines. In a parameter sweep, the value
of a parameter is adjusted by sweeping the parameter values through a
user defined range. For example, you can use the `-p velvet
?hash_length=29-37:4` option in the `ar-run` command to launch three
velvet jobs with different hash lengths (29, 33, 37). Here, for
numerical parameters, the general syntax is: ``` module
?parameter=beg-end:step_size ```

To list the pipeline and parameter details for the jobs you have
launched, type:

```inv
ar-stat --detail
```
```out
+--------+---------+----------------------+----------+------------------+-----------------------------------------------+
| Job ID | Data ID |        Status        | Run time |   Description    | Parameters                                    |
+--------+---------+----------------------+----------+------------------+-----------------------------------------------+
|  218   |   143   |       Complete       | 0:02:26  |    kmer sweep    | -p 'none tagdust' velvet ?hash_length=29-37:4 |
|  224   |   152   |       Complete       | 0:18:24  |   first: auto    | -p auto                                       |
|  225   |   153   |       Complete       | 0:11:37  |   RAST recipe    | -r rast                                       |
|  227   |   157   |       Complete       | 0:00:21  |       None       | -p velvet                                     |
+--------+---------+----------------------+----------+------------------+-----------------------------------------------+
```


### PacBio support

The assembly service supports an experimental version of the HGAP
pipeline for assembling PacBio reads. Here's an example:

```inv
ar-run --single_url http://www.mcs.anl.gov/~fangfang/arast/m120404.bas.h5 -a pacbio ?min_long_read_length=3500 ?genome_size=40000
```

This command will assemble the lambda phage genome in a few minutes
from reads in the raw PacBio H5 format.


## Real data examples

Here we use the default recipe to assemble the Rhodobacter
sphaeroides genome from Illumina HiSeq reads (SRA accession: SRR522244).

As you can see from the visual evaluation below (generated using the
QUAST quality assessment tool), our merged assembly has a
significantly higher NGA50 value than any individual assembly. The
NGA50 value is the aligned N50 size when the reference genome (ground
truth) is provided. 

![quast assembly comparison table](http://www.mcs.anl.gov/~fangfang/arast/quast_1.png)

When you open the report HTML file included the analysis directory,
you can inspect the rankings of assembly pipelines in terms of
cumulative contig lengths by hovering the mouse over your selected set
of the top contigs.

![quast assembly comparison plot](http://www.mcs.anl.gov/~fangfang/arast/quast_2.png)



