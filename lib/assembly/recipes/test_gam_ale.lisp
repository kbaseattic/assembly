(begin
  (define assemblies (list (kiki READS) (velvet READS)))
  (define toptwo (slice (sort assemblies > :key (lambda (c) (arast_score c))) 0 2))
  (define gam (gam_ngs toptwo))
  (define newsort (sort (cons gam assemblies) > :key (lambda (c) (get ale_score (ale c)))))
  (tar (all_files (quast (upload newsort))) :name analysis)
)
