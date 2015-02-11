(begin
   (define ki (kiki READS))
   (tar (all_files (quast (upload (sort (list ki) > :key (lambda (c) (get ale_score (ale c))))))) :name analysis :tag quast)
)
