;;; Assembles with A6, Velvet and SPAdes (with BayesHammer for error correction).
;;; Results are sorted by ARAST quality Score.
(begin
  (define vt (velvet READS))
  (define sp (begin (setparam only_assembler False) (spades READS)))
  (if (has_paired READS)
    (prog
      (define aa (a6 READS))
      (define assemblies (list vt sp aa)))
    (define assemblies (list vt sp)))
  (define newsort (sort assemblies > :key (lambda (c) (arast_score c))))
  (tar (all_files (quast (upload newsort))) :name analysis)
)
