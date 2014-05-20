### Adapted from:
## (c) Peter Norvig, 2010; See http://norvig.com/lispy.html
################ Symbol, Env classes

import os
import itertools

#### Arast Libraries
import asmtypes

Symbol = str

class Env(dict):
    "An environment: a dict of {'var':val} pairs, with an outer Env."
    def __init__(self, parms=(), args=(), outer=None):
        self.update(zip(parms,args))
        self.outer = outer
        self.emissions = []
    def find(self, var):
        "Find the innermost Env where var appears."
        return self if var in self else self.outer.find(var)

def add_globals(env):
    "Add some Scheme standard procedures to an environment."
    import math, operator as op
    env.update(vars(math)) # sin, sqrt, ...
    env.update(
     {'+':op.add, '-':op.sub, '*':op.mul, '/':op.div, 'not':op.not_,
      '>':op.gt, '<':op.lt, '>=':op.ge, '<=':op.le, '=':op.eq, 
      'equal?':op.eq, 'eq?':op.is_, 'length':len, 'cons':lambda x,y:[x]+y,
      'car':lambda x:x[0],'cdr':lambda x:x[1:], 'append':op.add,  
      'list':lambda *x:list(x), 'list?': lambda x:isa(x,list), 
      'null?':lambda x:x==[], 'symbol?':lambda x: isa(x, Symbol)})
    return env

global_env = add_globals(Env())
isa = isinstance

################ eval

def eval(x, env=global_env):
    "Evaluate an expression in an environment."
    if isa(x, Symbol):             # variable reference
        return env.find(x)[x]
    elif not isa(x, list):         # constant literal
        return x                
    elif x[0] == 'quote':          # (quote exp)
        (_, exp) = x
        return exp
    elif x[0] == 'if':             # (if test conseq alt)
        (_, test, conseq, alt) = x
        return eval((conseq if eval(test, env) else alt), env)
    elif x[0] == 'set!':           # (set! var exp)
        (_, var, exp) = x
        env.find(var)[var] = eval(exp, env)
    elif x[0] == 'define':         # (define var exp)
        (_, var, exp) = x
        env[var] = eval(exp, env)
    elif x[0] == 'lambda':         # (lambda (var*) exp)
        (_, vars, exp) = x
        return lambda *args: eval(exp, Env(vars, args, env))
    elif x[0] == 'emit':          # (emit exp) Store each intermediate for return
        (_,  exp) = x
        val = eval(exp, env)
        env.emissions.append(val)
        return val
    elif x[0] == 'get':
        (_, key, exp) = x
        chain = eval(exp, env)
        assert type(chain) is WaspLink
        val = chain.get_value(key)
        if type(val) is asmtypes.FileSet:
            chain['default_output'] = val
            return chain
        else: # A value
            return val
    elif x[0] == 'begin':          # (begin exp*) Return each intermediate
        val = []
        for exp in x[1:]:
            val.append(eval(exp, env))
        return val
    else:                          # (proc exp*)
        exps = [eval(exp, env) for exp in x]
        proc = exps.pop(0)
        return proc(*exps)

################ parse, read, and user interaction

def read(s):
    "Read a Scheme expression from a string."
    return read_from(tokenize(s))

parse = read

def tokenize(s):
    "Convert a string into a list of tokens."
    return s.replace('(',' ( ').replace(')',' ) ').split()

def read_from(tokens):
    "Read an expression from a sequence of tokens."
    if len(tokens) == 0:
        raise SyntaxError('unexpected EOF while reading')
    token = tokens.pop(0)
    if '(' == token:
        L = []
        while tokens[0] != ')':
            L.append(read_from(tokens))
        tokens.pop(0) # pop off ')'
        return L
    elif ')' == token:
        raise SyntaxError('unexpected )')
    else:
        return atom(token)

def atom(token):
    "Numbers become numbers; every other token is a symbol."
    try: return int(token)
    except ValueError:
        try: return float(token)
        except ValueError:
            return Symbol(token)

def to_string(exp):
    "Convert a Python object back into a Lisp-readable string."
    return '('+' '.join(map(to_string, exp))+')' if isa(exp, list) else str(exp)

def repl(prompt='lis.py> '):
    "A prompt-read-eval-print loop."
    while True:
        val = eval(parse(raw_input(prompt)))
        if val is not None: print to_string(val)

def run(exp, env):
    return eval(parse(exp), env=env)


class WaspLink(dict):
    def __init__(self, module=None, link=None):
        self['link'] = link
        self['module'] = module
        self['default_output'] = ''
        self['data'] = None
        self['info'] = {}

    def insert_output(self, output, default_type, module_name):
        """ Parses the output dict of a completed module and stores the 
        data and information within the WaspLink object """
        for outtype, outvalue in output.items():
            name = '{}_{}'.format(module_name, outtype)
            if not type(outvalue) is list: 
                outvalue = [outvalue]

            ## Store default output
            if default_type == outtype:
                for f in outvalue:
                    if isinstance(f, asmtypes.FileSet):
                        self['default_output'] = f
                    else:
                        self['default_output'] = asmtypes.set_factory(outtype,[asmtypes.FileInfo(f)],
                                                                      name=name)
            ## Store all outputs and values
            outputs = []
            filesets = []
            are_files = False
            for out in outvalue:
                try:
                    if os.path.exists(out): # These are files, convert to FileInfo format
                        outputs.append(asmtypes.FileInfo(out))
                        are_files = True
                except: # Not a file
                    outputs = outvalue
                    break
            if are_files:
                filesets.append(asmtypes.set_factory(outtype, outputs, name=name))
            else:
                self['info'][outtype] = outputs if not len(outputs) == 1 else outputs[0]
        self['data'] = asmtypes.FileSetContainer(filesets)

    def get_value(self, key):
        if key in self['info']:
            return self['info']['key']
        return self['data'].find_type(key)[0]



class WaspEngine():
    def __init__(self, plugin_manager, job_data):
        self.constants_reads = 'READS'
        self.pmanager = plugin_manager
        self.assembly_env = add_globals(Env())
        self.assembly_env.update({k:self.get_wasp_func(k, job_data) for k in self.pmanager.plugins})

        init_link = WaspLink()
        init_link['default_output'] = job_data.wasp_data().readsets
        self.assembly_env.update({self.constants_reads: init_link})
        self.assembly_env.update({'best_contig': wasp_functions.best})
        
    def run_wasp(self, exp, job_data):
        ## Run Wasp expression
        if type(exp) is str or type(exp) is unicode:
            w_chain = run(exp, self.assembly_env)
        elif type(exp) is list:
            w_chain = eval(exp, env=env)
        ## Record results into job_data
        if type(w_chain) is not list: # Single
            w_chain = [w_chain]
        for w in w_chain + self.assembly_env.emissions:
            try: job_data.add_results(w['default_output'])
            except: pass
        return job_data

    def get_wasp_func(self, module, job_data):
         def run_module(*inlinks):
            # WaspLinks keep track of the recursive pipelines
             wlink = WaspLink(module, inlinks)
             self.pmanager.run_proc(module, wlink, job_data)
             return wlink
         return run_module

###### Utitlity
def _longest_common_exp(s1, s2):
    m = [[0] * (1 + len(s2)) for i in xrange(1 + len(s1))]
    longest, x_longest = 0, 0
    for x in xrange(1, 1 + len(s1)):
        for y in xrange(1, 1 + len(s2)):
            if s1[x - 1] == s2[y - 1]:
                m[x][y] = m[x - 1][y - 1] + 1
                if m[x][y] > longest:
                    longest = m[x][y]
                    x_longest = x
            else:
                m[x][y] = 0
    lcs = s1[x_longest - longest: x_longest]
    
    #### Remove extra parens
    open_parens = lcs.count('(')
    close_parens = lcs.count(')')
    if open_parens and close_parens >= open_parens:
        return lcs[:-(close_parens - open_parens)]

def pipelines_to_exp(pipes):
    all_pipes = []
    for pipe in pipes:        
        exp = 'READS'
        for m in pipe:
            exp = '({} {})'.format(m, exp)
        exp = '(emit {})'.format(exp)
        all_pipes.append(exp)
        
    #### Check for duplicates and redefine
    val_num = 0
    replacements = []
    defs = []
    reversed_pairs = set()
    lces = set()
    for pipe1, pipe2 in itertools.permutations(all_pipes, 2):
        reversed_pairs.add((pipe2, pipe1))
        if not (pipe1, pipe2) in reversed_pairs:
            lce = _longest_common_exp(pipe1, pipe2)
            if lce not in lces and lce:
                lces.add(lce)
                replacements.append((lce.strip(), 'val{}'.format(val_num)))
                defs.append('(define val{} {})'.format(val_num, lce.strip()))
                val_num += 1

                
    #### Replace defined expressions
    for replacement in replacements:
        for i, pipe in enumerate(all_pipes):
            all_pipes[i] = pipe.replace(*replacement)
    
    #### Form final expression
    final_exp = '(begin {} (quast {}))'.format(' '.join(defs), ' '.join(all_pipes))
    return final_exp
