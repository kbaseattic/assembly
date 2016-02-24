;;; Assembles with Velvet and MEGAHIT.
;;; Results are sorted by ARAST quality Score.
;;; Works for some short read datasets.
(begin
  (define vt (velvet READS))
  (define mh (megahit READS))
  (define assemblies (list vt mh))
  (define newsort (sort assemblies > :key (lambda (c) (arast_score c))))
  (tar (all_files (quast (upload newsort))) :name analysis)
)
