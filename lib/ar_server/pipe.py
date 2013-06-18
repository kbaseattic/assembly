import itertools
import re

"""
# parameter sweep
input: ['trim_sort', 'kiki', '?k=29-30']
output: [['trim_sort', 'kiki', '?k=29], ['trim_sort', 'kiki', '?k=30]]

# parameter sweep with multiple assemblers
input: ['trim_sort', 'kiki ?k=29-30 velvet']
output: [['trim_sort', 'kiki', '?k=29], ['trim_sort', 'kiki', '?k=30], ['trim_sort', 'velvet']]

# binary parameter sweep
CLI: trim_sort kiki ?k=29-30 ?cov=20-21
input: ['trim_sort', 'kiki', '?k=29-30', ?cov=20-21]
output: [['trim_sort', 'kiki', '?k=29, '?cov=20], ['trim_sort', 'kiki', '?k=30, '?cov=20],
         ['trim_sort', 'kiki', '?k=29, '?cov=21], ['trim_sort', 'kiki', '?k=30, '?cov=21]]

"""
#my_pipe = ['trim_sort', '?length=10-11', 'kiki ?k=29-30 ?cov=29-30']
my_pipe = ['ma', '?k=1,5,3', 'b']
#my_pipe = ['a' , 'b ?k=1,10-11,20,30:40:2']
test=['sga_preprocess', '?min_length=29,100,150','sga_ec', 'tagdust',
      'velvet ?hash_length=31:39:2 idba']
def parse_pipe(pipe):
    """
    Parses modules and parameters into stages
    Input: a flat (no quotes) list of modules and params
      e.g. ['kiki', '?k=29-30', 'velvet']
    Output: list of lists containing single modules and
      parameters
      e.g. [['kiki', '?k=29'], ['kiki', '?k=30'], ['velvet']]
    """
    module = []
    stages = []
    for string in pipe:
        if not string.startswith('?'):
            if module:
                stages.append(module) #flush
                module = [string]
            else:
                module.append(string)
        else:
            module.append(string) #param
    if module:
        stages.append(module)
    stages = [expand_sweep(m) for m in stages]
    return stages

def parse_branches(pipe):
    stages = []
    flat_pipe = []
    for i in range(len(pipe)):
        if len(pipe[i].split(' ')) == 1:
            flat_pipe.append(pipe[i])
            try:
                if len(pipe[i+1].split(' ')) != 1:
                    stages += parse_pipe(flat_pipe)
                    flat_pipe = []
            except:
                stages += parse_pipe(flat_pipe)
                flat_pipe = []
        else: # parenth
            stages += [list(itertools.chain(*parse_pipe(pipe[i].split(' '))))]
            
    cart = [list(itertools.product(*stages))]
    all_pipes = []
    for pipe in cart[0]:
        all_pipes.append(list(itertools.chain(*pipe)))
    return all_pipes
   
def expand_sweep(module):
    """
    [m, ?p=1-2, ?p=3-4] -> [m, p1, p3, m, p2, p3, m, p1, p4, m, p1, p4]
    """
    expanded = []
    has_range = False
    for word in module:
        if word.startswith('?'):
            f = re.split('\?|=', word)[1:]
            flag = f[0]
            params = f[1]
            sweep = []
            for param in params.split(','):
                s = re.split('-|:', param)
                if len(s) != 1: #is range
                    has_range = True
                    delim = s[0].find('=')+1
                    if delim == 1:
                        break
                    srange = (int(s[0][delim:]),int(s[1]))
                    step_size = 1
                    if len(s) == 3:
                        step_size = int(s[2])
                    sweep += ['?{}={}'.format(flag, x) 
                             for x in range(
                            srange[0], srange[1]+1, step_size)]
                else:
                    sweep.append('?{}={}'.format(flag, s[0]))
                    has_range = True
            expanded.append(sweep)                    
        else: #mod name
            expanded.append([word])

    if has_range:
        cart = [list(itertools.product(*expanded))]
        flat = list(itertools.chain(*cart))
        return flat
    else:
        return [module]


#print parse_branches(my_pipe)
