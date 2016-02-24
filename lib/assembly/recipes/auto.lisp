;;; For short reads:
;;;   1. Runs BayesHammer on reads
;;;   2. Assembles with Velvet, IDBA and SPAdes
;;;   3. Sorts assemblies by ALE score
;;; For long reads (PacBio or Nanopore):
;;;   Assembles with MiniASM
(begin
  (if (has_short_reads_only READS)
      (prog
	(define pp (bhammer READS))
	(if (not (symbol? pp))
	    (define pp READS))
	(define vt (velvet pp))
	(define sp (spades pp))
	(if (has_paired READS)
	  (prog
	    (define id (idba pp))
	    (define assemblies (list id sp vt)))
	  (define assemblies (list sp vt))))
     (define assemblies (list (miniasm READS))))

  (define sorted (sort assemblies > :key (lambda (c) (arast_score c))))
  (tar (all_files (quast (upload sorted))) :name analysis)
)
