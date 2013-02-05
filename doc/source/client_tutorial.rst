Using the Assembly Service Command-Line Client
==============================================

Introduction
------------
The DOE KBase features an Assembly Service with tools that allow users to submit a variety of sequence datasets to be processed, assembled, and analyzed.  This tutorial will introduce you to the current capabilities of the service as well as give some command-line recipes.

Currently at an early phase, the Assembly Service has the following computation capabilities:

* Velvet assembly
* Kiki assembly

Here we will walk through a couple examples.

Authentication
--------------
To authenticate using one's GlobusOnline ID or switch to a different account, use the ar_login command::

  ar_login

  ar_logout


Assembling Single-End Reads wih Velvet
---------------------------------------
Here we will use a sample metagenome file called `se.fastq`_

.. _`se.fastq`: http://www.mcs.anl.gov/~fangfang/test/se.fastq

::

  wget http://www.mcs.anl.gov/~fangfang/test/se.fastq

1. Submit the file to be assembled with velvet::

    ar_run -f se.fastq -a velvet -m "Description of job"

2. Check and monitor the status of your jobs::

    ar_stat -w

Output::

  +--------+---------+-----------------------------------------+----------+-------------+
  | Job ID | Data ID |                  Status                 | Run time | Description |
  +--------+---------+-----------------------------------------+----------+-------------+
  |   83   |    40   |           pipeline [success]            | 0:22:29  |     None    |
  |   92   |    40   |              Running: [4%]              | 0:00:22  |     None    |
  |   93   |    41   |           pipeline [success]            | 0:00:03  |     None    |
  |   94   |    44   |           pipeline [success]            | 0:22:08  |     None    |
  +--------+---------+-----------------------------------------+----------+-------------+

3. Get assembly data upon completion::

    ar_get -j 94

The assembly service will download 3 files

* **JOB_ID_report.txt**:  a general log of commands run and files used
* **JOB_ID_assemblies.tar.gz**:  a compressed archive of assembler data
* **JOB_ID_analysis.tar.gz**:  assembly analysis performed via QUAST_

.. _QUAST: http://bioinf.spbau.ru/quast


Assembling Pair-End Reads wih Kiki and Velvet
---------------------------------------------
We will walk through the creation and comparison of two assemblies using Kiki and Velvet.
Here we will use sample paired end files called `pe_1.fastq`_ and `pe_2.fastq`_

.. _`pe_1.fastq`: http://www.mcs.anl.gov/~fangfang/test/pe_1.fastq
.. _`pe_2.fastq`: http://www.mcs.anl.gov/~fangfang/test/pe_2.fastq

::

  wget http://www.mcs.anl.gov/~fangfang/test/pe_1.fastq
  wget http://www.mcs.anl.gov/~fangfang/test/pe_2.fastq

1. Submit the file to be assembled with kiki and velvet::

    ar_run --pair pe_1.fastq pe_2.fastq -a kiki velvet -m "Description of job"

2. Check and monitor the status of your jobs::

    ar_stat -w

Output::

  +--------+---------+-----------------------------------------+----------+-------------+
  | Job ID | Data ID |                  Status                 | Run time | Description |
  +--------+---------+-----------------------------------------+----------+-------------+
  |   83   |    40   |           pipeline [success]            | 0:22:29  |     None    |
  |   92   |    40   |              Running: [4%]              | 0:00:22  |     None    |
  |   93   |    41   |           pipeline [success]            | 0:00:03  |     None    |
  |   94   |    44   |           pipeline [success]            | 0:22:08  |     None    |
  |   95   |    44   |              Running: [50%]             | 0:00:08  |     Test    |
  +--------+---------+-----------------------------------------+----------+-------------+

3. Get assembly data upon completion::

    ar_get -j 95

Once again, the assembly service will download 3 files:

* *JOB_ID_report.txt*: a general log of commands run and files used
* *JOB_ID_assemblies.tar.gz*: a compressed archive of assembler data
* *JOB_ID_analysis.tar.gz*: assembly analysis performed via QUAST_

4. Look at QUAST analysis by extracting the analysis archive::

    mkdir results
    tar -xf 95_analysis.tar.gz -C results/
    cat results/report.txt

Output::

  Assembly                   P1_Ki    P2_Vt  
  # contigs (>= 0 bp)        6579     12317  
  # contigs (>= 1000 bp)     309      190    
  Total length (>= 0 bp)     2698557  2573302
  Total length (>= 1000 bp)  1246799  273827 
  # contigs                  730      978    
  Largest contig             107620   3356   
  Total length               1534546  800695 
  GC (%)                     40.84    41.95  
  N50                        4999     806    
  N75                        1275     617    
  # N's per 100 kbp          0.00     0.00 

Or open **report.html** for visualizations:

.. image:: quast.png

