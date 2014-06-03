auto = """
(begin
 (define sp (spades READS))
 (define id (idba READS))
 (define gam (gam_ngs sp id))
 (quast (emit (sspace READS gam)) (emit (get scaffolds sp)) (emit (get scaffolds id)))
)
"""




jigsaw = '''  '''


