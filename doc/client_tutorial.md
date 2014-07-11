# Using the Assembly Service Commands

## Introduction 

The Assembly Service is a web-based environment that allows users to
submit sequence datasets to be processed, assembled, and analyzed. 
This tutorial will introduce you to the current capabilities of the
service as well as give some command-line recipes. You will learn how
to upload a set of read files, assemble them, inspect the results, and
get the best assembly for your downstream analysis. 

We believe the default pipeline performs well. However, we encourage
you to experiment with alternative assemblers, preprocessing tools,
and parameter settings. Our service currently supports over 20
assemblers and tools, and its modular design allows for
straightforward extension as sequencing technologies and analysis
tools evolve. We have also built a powerful pipeline engine that
allows you to mix and match approaches and evaluate a variety of
customized pipelines on your datasets.

We will start with a very simple example. Then, we will step through
the commands and options. Since a thorough assembly on a microbial
genome can take hours, we will be using a partial dataset in the early
examples for quick turnaround. In the final set of examples, we will
work with some real data. This tutorial will focus on microbial
assembly, although some of the modules included in the service
supports assembly of low-complexity metagenomes.

## A Simple Example

The following command will instruct the server to download a file of
single-end reads specified by the URL and assemble them using the
velvet assembler. This should take just a couple minutes. 

```inv
ar-run -a velvet --single_url http://www.mcs.anl.gov/~fangfang/arast/se.fastq | ar-get --wait -p > ex1.contigs.fasta
```

This command will block until the assembly is done. The resulting set
of contigs will be saved to a FASTA file local to the client. The
choice of output name is arbitrary; we use `ex1.contigs.fasta` to
denote it's the contigs from our first exercise. You can use the Unix
`cat` command to inspect the content of the contig file.

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

This command uses two operators on Unix-like systems: the pipe
operator `|` for chaining commands, and the redirection operator `>`
to save output normally directed to the screen to a designated
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
have to local sequence files named `p1.fq` and `p2.fq`:

```inv
ar-upload --pair p1.fq p2.fq > ex2.data_id
```

The upload will return a data ID from the server. The data ID allows
you to invoke different assemblers or pipelines on the same data
without resubmitting it. In the example above, we have used the
`> ex2.data_id` pipe function to save the data ID to a file. If you omit
that part, an integer ID will be printed to the screen upon successful
submission.

### Launching an assembly job

To launch our default assembly pipeline on the dataset you submitted
in the previous section, you can simply type:

```inv
cat ex2.data_id | ar-run > ex3.job_id
```

If you don't have the data ID saved in a file, you can instead type
something such as `ar-run --data 23`.

Note that the assembly job is asynchrnous. The `ar-run` command should
return immediately with a job ID with which you can query the job
status.

As we have shown in our very first example, you can also bypass the
`ar-upload` step and launch a job directly. Here is an example.

```inv
ar-run --pair p1.fq p2.fq | ar-run -p tagdust idba -m "my test job"
```

This command should return as soon as the data is uploaded. Note that we
are also explicitly invoking the `tagdust` preprocessing module and
the `idba` assembler using the `-p` pipeline option. You can use the
`ar-avail` command to list all the modules supported. We will describe
those and the pipeline support in the Advanced Features section.

Both the `ar-run` and `ar-upload` commands allow you to specify a
reference genome with the `--reference genome.fasta` option. It will
be used to score the assemblies in the evaluation step. 

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
|  140   |    68   |   Stage 2/3: idba    | 0:00:59  |       None       |
|  141   |    70   |       Complete       | 0:00:21  |   RAST recipe    |
|  142   |    71   | Stage 2/5: kmergenie | 0:00:30  |   kmer tuning    |
+--------+---------+----------------------+----------+------------------+
```

When a job is in progress, its stage information is updated in the
Status field; otherwise, it can end in one of the following states:
"Complete", "Complete with error", "Terminated", and "FAIL[description]".
You can use the `ar-stat -j job_id` command to inspect the error
message for a failed job.

You may notice that of the two jobs we just launched, the second one
may be the first to finish. That's because our default pipeline
invokes multiple assemblers on your dataset with parameter tuning. It
may even try to reconcile and merge the best individual assemblies.

The status table also gives you the data ID for each job. However, you
may need to list all the datasets you have uploaded but may not
necessarily have computed on. For that, you can type:

```inv
ar-stat -l
```

### Getting assembly results

Once a job completes, you can look at the report of assembly
statitistics and pick your best set of contigs. You can also choose to
download the whole data directory which includes detailed log files
and a visual comparison of all the assemblies.

Use `ar-get -j job_id --report` to show the text assembly report. You
can add the `--wait` option to make sure the command waits for the job
to complete. In the following example, we specify the job ID from a
file we have saved.

```inv
cat ex3.job_id | ar-get --report --wait
```

You can pick an assembly using numeric or string IDs (e.g.,
`ar-get --pick 2`, `ar-get --pick spades_contigs`). By default,
we will get you the best assembly based on a set of common metrics.
We are still working on the scoring functions for reference-based
and reference-free assemblies.

```inv
cat ex3.job_id | ar-get --wait > ex4.contigs.fasta
```

To download the whole assembly directory on the server, type:

```inv
cat ex3.job_id | ar-get -o ex5.dir
```

Here's an example of an HTML file in the downloaded diretory for
visually comparing multiple assemblies (currently supported by
the `quast` module).

![quast assembly comparison](http://www.mcs.anl.gov/~fangfang/arast/quast.png)


## Advanced Features

### More options

PacBio assembly
URL support

### Modules

multiple preprocessing modules
usually one assembler

### Parameters

### Pipelines

### Recipes

## Real data examples

### Buchnera

### Ecoli or MTB


