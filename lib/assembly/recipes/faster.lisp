;;; Assembles with A6 and Velvet.
;;; Results are sorted by ARAST quality Score.
;;; Works for some short read datasets.
(begin
  (define vt (velvet READS))
  (if (has_paired READS)
    (prog
      (define aa (a6 READS))
      (define assemblies (list vt aa)))
    (define assemblies (list vt)))
  (define newsort (sort assemblies > :key (lambda (c) (arast_score c))))
  (tar (all_files (quast (upload newsort))) :name analysis)
)
