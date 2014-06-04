auto2 = """
(begin
 (define pp (bhammer (sga_preprocess READS)))
 (define sp (spades pp))
 (define id (idba pp))
 (define gam (gam_ngs sp id))
 (quast (emit (sspace pp gam)) (emit (get scaffolds sp)) (emit (get scaffolds id)))
)
"""

auto = """
(begin
 (define pp READS)
 (define kval (get best_k (kmergenie pp)))
 (define vt (begin (setparam hash_length kval) (velvet pp)))
 (define sp (spades pp))
 (define id (idba pp))
 (define gam (gam_ngs (slice (sort (list sp id vt) > :key (lambda (c) (n50 c))) 0 2)))
 (quast (emit (sspace pp gam)) (emit (get scaffolds sp)) (emit (get scaffolds id)) (emit (sspace pp vt)))
)

"""


