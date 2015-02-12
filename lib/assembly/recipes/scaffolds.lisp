(begin
  (define pp (bhammer (sga_preprocess READS)))
  (define sp (spades pp))
  (define id (idba pp))
  (define gam (gam_ngs sp id))
  (quast (upload (sspace pp gam)) (upload (get scaffolds sp)) (upload (get scaffolds id)))
)
