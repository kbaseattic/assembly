;;; Runs BayesHammer on reads and assembles with plasmidSPAdes.
(begin
  (define sp (begin (setparam only_assembler False) (plasmid_spades READS)))
  (tar (all_files (quast (upload (sort (list sp) > :key (lambda (c) (arast_score c)))))) :name analysis :tag quast)
)
