;;; Runs Velvet with hash length 35.
;;; Runs BayesHammer on reads and assembles with SPAdes with k up to 99.
;;; Results are sorted by ARAST quality score.
;;; Works for Illumina MiSeq reads.
(begin
  (define vt (begin (setparam hash_length 35) (velvet READS)))
  (define sp (begin
     (setparam only_assembler False)
     (setparam read_length medium2)
     (spades READS)))
  (tar (all_files (quast (upload (sort (list vt sp) > :key (lambda (c) (arast_score c)))))) :name analysis :tag quast)
)
