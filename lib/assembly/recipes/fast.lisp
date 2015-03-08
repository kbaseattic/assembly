;;; Assembles with A6, Velvet and MEGAHIT.
;;; Results are sorted by ARAST quality Score.
(begin
  (define vt (velvet READS))
  (define mh (megahit READS))
  (if (has_paired READS)
    (prog
      (define aa (a6 READS))
      (define assemblies (list vt mh aa)))
    (define assemblies (list vt mh)))
  (define newsort (sort assemblies > :key (lambda (c) (arast_score c))))
  (tar (all_files (quast (upload newsort))) :name analysis)
)
