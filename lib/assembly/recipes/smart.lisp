;;; For short reads:
;;;   1. Runs BayesHammer on reads, Kmergenie to choose hash-length for Velvet
;;;   2. Assembles with Velvet, IDBA and SPAdes
;;;   3. Sorts assemblies by ALE score
;;;   4. Merges the two best assemblies with GAM-NGS
;;; For long reads (PacBio or Nanopore):
;;;   Assembles with MiniASM
(begin
  (if (has_short_reads_only READS)
      (prog
	(define pp (bhammer READS))
	(if (not (symbol? pp))
	    (define pp READS))
	(define kval (get best_k (kmergenie pp)))
	(define vt (begin (setparam hash_length kval) (velvet pp)))
	(define sp (spades pp))
	(if (has_paired READS)
	  (prog
	    (define id (idba pp))
	    (define assemblies (list id sp vt)))
	  (define assemblies (list sp vt)))
	(define toptwo (slice (sort assemblies > :key (lambda (c) (arast_score c))) 0 2))
	(define gam (gam_ngs toptwo))
	(define newsort (sort (cons gam assemblies) > :key (lambda (c) (arast_score c))))
	(tar (all_files (quast (upload newsort))) :name analysis))
    (prog
      (define assemblies (list (miniasm READS)))
      (tar (all_files (quast (upload (sort assemblies > :key (lambda (c) (arast_score c)))))) :name analysis :tag quast)))
)
