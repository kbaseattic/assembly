auto = """
(begin
 (define pp (bhammer (sga_preprocess READS)))
 (define sp (spades pp))
 (define id (idba pp))
 (define gam (gam_ngs sp id))
 (quast (emit (sspace pp gam)) (emit (get scaffolds sp)) (emit (get scaffolds id)))
)
"""




jigsaw = '''  '''


