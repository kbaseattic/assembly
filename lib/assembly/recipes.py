scaffolds = """
(begin
 (define pp (bhammer (sga_preprocess READS)))
 (define sp (spades pp))
 (define id (idba pp))
 (define gam (gam_ngs sp id))
 (quast (upload (sspace pp gam)) (upload (get scaffolds sp)) (upload (get scaffolds id)))
)
"""

auto333 = """
(begin
 (define pp (bhammer READS))
 (define kval (get best_k (kmergenie READS)))
 (define vt (begin (setparam hash_length kval) (velvet pp)))
 (define ki (begin (setparam k kval) (kiki pp)))
 (define sp (spades pp))
 (define id (idba pp))
 (define ma (masurca pp))
 (define di (discovar pp))
 (define allsort (sort (list sp id vt ki ma di) > :key (lambda (c) (get ale_score (ale c)))))
 (define gam (gam_ngs (slice allsort 0 3)))
 (tar (all_files (quast gam di ma id sp ki vt) :name analysis))
)

"""

super = """
(begin
 (define pp (bhammer READS))
 (define kval (get best_k (kmergenie READS)))
 (define vt (begin (setparam hash_length kval) (velvet pp)))
 (define sp (spades pp))
 (define id (idba pp))
 (define ma (masurca pp))
 (define di (discovar pp))
 (define gam (gam_ngs (sort (list sp id vt ma di) > :key (lambda (c) (n50 c)))))
 (tar (all_files (quast (upload gam) (upload sp) (upload id) (upload vt) (upload ma) (upload di))) :name analysis)
)

"""

auto = """
(begin
 (define pp (bhammer READS))
 (define kval (get best_k (kmergenie READS)))
 (define vt (begin (setparam hash_length kval) (velvet pp)))
 (define sp (spades pp))
 (define allsort (sort (list sp vt) > :key (lambda (c) (get ale_score (ale c)))))
 (define gam (gam_ngs allsort))
 (define newsort (sort (list gam sp vt) > :key (lambda (c) (get ale_score (ale c)))))
 (tar (all_files (quast newsort) :name analysis))
)
"""
