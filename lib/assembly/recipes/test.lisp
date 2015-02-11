(begin
  (define newsort (sort (list (kiki READS) (velvet READS)) > :key (lambda (c) (arast_score c))))
  (tar (all_files (quast (upload newsort))) :name analysis :tag quast)
)
