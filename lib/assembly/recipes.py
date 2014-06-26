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

superduper = """
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
 (define kval (get best_k (kmergenie pp)))
 (define vt (begin (setparam hash_length kval) (velvet pp)))
 (define sp (spades pp))
 (define id (idba pp))
 (define toptwo (slice (sort (list id sp vt) > :key (lambda (c) (n50 c))) 0 2))
 (define gam (gam_ngs toptwo))
 (define newsort (sort (list gam sp vt id) > :key (lambda (c) (get ale_score (ale c)))))
 (tar (all_files (quast (upload newsort))) :name analysis)
)
"""


tune_velvet = """
(begin
 (define pp (sga_preprocess READS))
 (define bh (bhammer READS))
 (define ppbh (bhammer pp))
 (define kpp (get best_k (kmergenie pp)))
 (define kbh (get best_k (kmergenie bh)))
 (define kppbh (get best_k (kmergenie ppbh)))
 (define k (get best_k (kmergenie READS)))
 (define vtpp (begin (setparam hash_length kpp) (velvet pp)))
 (define vtbh (begin (setparam hash_length kbh) (velvet bh)))
 (define vtppbh (begin (setparam hash_length kppbh) (velvet ppbh)))
 (define vt (begin (setparam hash_length k) (velvet READS)))
 (tar (all_files (quast vt vtpp vtbh vtppbh)) :name analysis))
)
"""



test = """
(begin
 (define newsort (sort (list (kiki READS) (velvet READS)) > :key (lambda (c) (n50 c))))
 (tar (all_files (quast (upload newsort))) :name analysis)
)
"""


