;;; 1. Runs BayesHammer on reads
;;; 2. Assembles with Velvet, IDBA and SPAdes
;;; 3. Sorts assemblies by ALE score
(begin
  (define pp (bhammer READS))
  (if (not (symbol? pp))
      (prog
       (define pp READS)))
  (define vt (velvet pp))
  (define sp (spades pp))
  (if (has_paired READS)
    (prog
      (define id (idba pp))
      (define assemblies (list id sp vt)))
    (define assemblies (list sp vt)))
  (define newsort (sort assemblies > :key (lambda (c) (arast_score c))))
  (tar (all_files (quast (upload newsort))) :name analysis)
)
