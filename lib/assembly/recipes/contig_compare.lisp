;;; Compares multiple assembled contig sets with QUAST
(begin
 (define contigs CONTIGS)
 (define newsort (sort (list contigs) > :key (lambda (c) (arast_score c))))
 (tar (all_files (quast contigs)) :name analysis)
 )
