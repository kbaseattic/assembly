### Adapted from:
## (c) Peter Norvig, 2010; See http://norvig.com/lispy.html
################ Symbol, Env classes

from __future__ import division

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
    elif x[0] == 'emit':          # (begin exp*) Return each intermediate
        (_,  exp) = x
        val = eval(exp, env)
        env.emissions.append(val)
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
    def __init__(self, module, link):
        self['link'] = link
        self['module'] = module
        self['default_output'] = ''


class WaspEngine():
    def __init__(self, plugin_manager, job_data):
        self.pmanager = plugin_manager
        self.assembly_env = add_globals(Env())
        self.assembly_env.update({k:self.get_wasp_func(k, job_data) for k in self.pmanager.plugins})

    def run_wasp(self, exp, job_data):
        ## Run Wasp expression
        w_chain = run(exp, self.assembly_env)
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
            # Outputs a single "link"

            ### Case: Tail recursive call
             jd = job_data
             if inlinks[0] == 1: ## Indicate reads
                 # Empty link
                 inlinks = (WaspLink(str(inlinks[0]), None),)

             wlink = WaspLink(module, inlinks)
             self.pmanager.run_proc(module, wlink, jd)
             return wlink
         return run_module
