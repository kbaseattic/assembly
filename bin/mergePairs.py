#!/usr/bin/python
#mergePairs.py
#Jeremy Leipzig
#merge overlapping paired end reads to improve assemblies

from optparse import OptionParser
from Bio.SeqIO.QualityIO import FastqGeneralIterator
from Bio.Seq import Seq
from Bio import pairwise2
import itertools
from Bio.SeqRecord import SeqRecord
from Bio.Alphabet import IUPAC
from Bio import SeqIO
import numpy as np
from StringIO import StringIO


usage = "usage: %prog [options] FILE1 FILE2"
parser = OptionParser(usage=usage)

parser.add_option("-i", "--insert", action="store", type="int", dest="insert",
                  help="insert length of fragment from end to end (|s1---s2|)",metavar="insert length (default:%default)",default=125)
parser.add_option("-e", "--error", action="store", type="int", dest="error",
                  help="amount of error in either direction (--insert 125 --error 50 => 75bp-175bp range) (default:%default)",default=50,metavar="error")
parser.add_option("-m", "--minimum", action="store", type="int", dest="minimum",
                  help="absolute minimum acceptable bp overlap for pairs to be merged (default: 5)",default=5,metavar="minimum")
parser.add_option("-g", "--merged", action="store", type="string", dest="merged",
                  help="output file for successfully merged pairs (default merged.fq)",metavar="mergedFileName.fq",default="merged.fq")
parser.add_option("-u", "--unmerged", action="store", type="string", dest="unmerged",
                  help="output file for unmerged pairs (default: unmerged.fq)",metavar="unmergedFileName.fq",default="unmerged.fq")
parser.add_option("-d", "--identity", action="store", type="int", dest="identity",
                  help="minimum percent sequence identity within overlap (default: 90)",default=90,metavar="sequence identity")
parser.add_option("-s", "--intypenum", action="store", type="int", dest="intypenum",
                  help="use number to indicate input seq format 1:fastq-sanger, 2:fastq-illumina, 3:fastq-solexa",default=1,metavar="input sequence format")
parser.add_option("-o", "--outtypenum", action="store", type="int", dest="outtypenum",
                  help="use number to indicate output seq format 1:fastq-sanger, 2:fastq-illumina, 3:fastq-solexa, 4:fasta",default=1,metavar="input sequence format")

(options, args) = parser.parse_args()
if len(args) != 2:
	parser.error("incorrect number of arguments")
else:
	fwd=args[0]
	rev=args[1]

merged_handle = open(options.merged, "w")
unmerged_handle = open(options.unmerged, "w")
preserve_handle = open("preserved.fq","w")

def merge_pairs(seq1, id1, q1, seq2, id2, q2):
		global merged
		exact_pos = seq1.find(seq2[0:options.minimum])
		if exact_pos >= 0:
				seq2_region = seq2[0:len(seq2)-(len(seq1)-exact_pos)]
				#this matrix is necessary otherwise N-N alignments are considered matches
				jerm={('A', 'A'): 1, ('A', 'C'): -1, ('A', 'T'): -1, ('A', 'G'): -1,
				      ('G', 'G'): 1, ('G', 'C'): -1, ('G', 'T'): -1,
				      ('C', 'C'): 1, ('C', 'T'): -1, 
				      ('T', 'T'): 1,
				      ('N','N'): -1,('N','A'): -1,('N','C'): -1,('N','G'): -1,('N','T'): -1}

                                #+1/-1 scoring is somehow necessary, a 1/0 scoring tends to produce awful end-alignments
				alignments = pairwise2.align.globalds(seq1,seq2,jerm,-1,-1,penalize_end_gaps=False,one_alignment_only=True)
				#print len(alignments)
				if len(alignments) < 1:
					printUnmerged(id1,seq1,q1,id2,seq2,q2)
				for seq_a, seq_b, score, start, end in alignments:
					overlap=len(seq1)+len(seq2)-(end-start)
					endgaps=(end-start)-overlap
					#e.g.with this matrix an overlap of 5 with 1 mismatch will be 80%ID but score a 3
					# 3>=5-5*2*(1-(80/100))
					# 3>=5-5*2*.2
					# 3>=5-2 ok
					if score>=overlap-overlap*2*(1-(options.identity/100.0)):
						#print seq_a
						#print seq_b
						apos=0
						bpos=0
						seq=''
						qual=''
						for (a1,a2) in itertools.izip(seq_a,seq_b):
							if (a1=='-' or a1 == 'N') and (a2=='-' or a2 == 'N'):
									#print "ambiguity"
									seq=''
									qual=''
									printUnmerged(id1,seq1,q1,id2,seq2,q2)
									break
							else:
								if (a1=='-'):
									seq+=a2
									qual+=q2[bpos]
									bpos+=1
								elif (a2=='-'):
									seq+=a1
									qual+=q1[apos]
									apos+=1
								elif (a1=='N'):
									seq+=a2
									qual+=q1[bpos]
									apos+=1
									bpos+=1
								elif (a2=='N'):
									seq+=a1
									qual+=q1[apos]
									apos+=1
									bpos+=1
								elif a1!='-' and a2!='-' and a1!='N' and a2!='N':
									if q1[apos]>q2[bpos]:
										seq+=a1
										qual+=q1[apos]
									else:
										seq+=a2
										qual+=q2[bpos]
									apos+=1
									bpos+=1
						if(len(seq)>0):
							#print id1,len(seq1),len(seq2),apos,bpos
							#http://biostar.stackexchange.com/questions/967/how-do-i-create-a-seqrecord-in-biopython
							printMerged(id1,seq,qual)
							printPreserved(id1,seq1,q1,id2,seq2,q2)
							assert(apos==len(seq1))
							assert(bpos==len(seq2))
							merged+=1
					else:
						printUnmerged(id1,seq1,q1,id2,seq2,q2)
					#print score + "is > " + identity + "of " + overlap
		else:
			printUnmerged(id1,seq1,q1,id2,seq2,q2)

def printUnmerged(id1,seq1,q1,id2,seq2,q2):
		fastq_string = "@%s\n%s\n+\n%s\n" % (id1, seq1, q1)
		record = SeqIO.read(StringIO(fastq_string), formats[options.intypenum])
		unmerged_handle.write(str(record.format(formats[options.outtypenum])))
		fastq_string = "@%s\n%s\n+\n%s\n" % (id2, seq2, q2)
		record = SeqIO.read(StringIO(fastq_string), formats[options.intypenum])
		unmerged_handle.write(str(record.format(formats[options.outtypenum])))

def printPreserved(id1,seq1,q1,id2,seq2,q2):
		fastq_string = "@%s\n%s\n+\n%s\n" % (id1, seq1, q1)
		record = SeqIO.read(StringIO(fastq_string), formats[options.intypenum])
		preserve_handle.write(str(record.format(formats[options.outtypenum])))
		fastq_string = "@%s\n%s\n+\n%s\n" % (id2, seq2, q2)
		record = SeqIO.read(StringIO(fastq_string), formats[options.intypenum])
		preserve_handle.write(str(record.format(formats[options.outtypenum])))
		
def printMerged(id1,seq,qual):
		fastq_string = "@%s\n%s\n+\n%s\n" % (id1, seq, qual)
		#print formats[options.intypenum] + " to " + formats[options.outtypenum]
		record = SeqIO.read(StringIO(fastq_string), formats[options.intypenum])
		merged_handle.write(str(record.format(formats[options.outtypenum])))


merged=0
count=0
formats={1:'fastq-sanger',2:'fastq-illumina',3:'fastq-solexa',4:'fasta'}
f_iter = FastqGeneralIterator(open(fwd,"rU"))
r_iter = FastqGeneralIterator(open(rev,"rU"))
for (f_id, f_seqstr, f_q), (r_id, r_seqstr, r_q) in itertools.izip(f_iter,r_iter):
	f_seq = Seq(f_seqstr)
	r_seq = Seq(r_seqstr)
	count += 2
	#Write out both reads with "/1" and "/2" suffix on ID
	#print f_id, f_seq, f_q, r_id, r_seq, r_q
	merge_pairs(str(f_seq).upper(),f_id,f_q,str(r_seq.reverse_complement()).upper(),r_id,r_q[::-1])




print "%i records written to %s" % (count, merged)
