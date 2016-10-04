(begin
 (define contigs CONTIGS)
 (upload (mummer contigs))
 (tar (all_files (quast contigs)) :name analysis)
 )
