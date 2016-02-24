### Adapted from:
## (c) Peter Norvig, 2010; See http://norvig.com/lispy.html
################ Symbol, Env classes

import os
import itertools
import uuid
import logging
import traceback, sys

#### Arast Libraries
import assembly as utils
import asmtypes
import wasp_functions as wf

logger = logging.getLogger(__name__)

Symbol = str

class Env(dict):
    "An environment: a dict of {'var':val} pairs, with an outer Env."
    def __init__(self, parms=(), args=(), outer=None, meta=None, job_data=None):
        self.update(zip(parms,args))
        self.outer = outer
        if outer is not None:
            self.emissions = outer.emissions
            self.uid = outer.uid
            self.meta = outer.meta
            self.global_data = outer.global_data
            self.plugins = outer.plugins
            self.exceptions = outer.exceptions
            self.errors = outer.errors
            self.outpath = outer.outpath
        else:
            self.emissions = []
            self.uid = job_data['uid']
            self.outpath = os.path.join(job_data['datapath'], str(job_data['job_id']))
            self.meta = meta
            self.global_data = {'stage': 1,
                                'stages': 0}

            self.plugins = []
            self.exceptions = []
            self.errors = []

        self.parameters = {}
        ### Updata job status

    def find(self, var):
        "Find the innermost Env where var appears."
        return self if var in self else self.outer.find(var)

    def next_stage(self, module=''):
        "Increment the stage and update the status"
        if module in self.plugins:
            try:
                self.meta.update_job(self.uid, 'status',
                                     'Stage {}/{}: {}'.format(self.global_data['stage'],
                                                              self.global_data['stages']
                                                              , module))
                self.global_data['stage'] += 1
            except: pass

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
      'null?':lambda x:x==[], 'symbol?':lambda x: isa(x, Symbol),
      'slice': lambda x,begin,end: x[begin:end]})
    return env

isa = isinstance

def eval(x, env):
    "Evaluate an expression in an environment."
    if isa(x, Symbol):             # variable reference
        try:
            return env.find(x)[x]
        except:
            raise Exception('Module "{}" not found'.format(x))
    elif not isa(x, list):         # constant literal
        return x
    elif x[0] == 'quote':          # (quote exp)
        (_, exp) = x
        return exp

    ####### Casting to FileSet Types
    elif x[0] in ['contigs', 'paired', 'single', 'reference']:
        wlink = WaspLink()
        eval_files = []
        try:
            for exp in x[1:]:
                eval_files += eval(exp, env).files
            wlink['default_output'] = asmtypes.set_factory(x[0], eval_files,
                                                           name='{}_override'.format(x[0]))
        except Exception as e:
            wlink['default_output'] = asmtypes.set_factory(x[0], x[1:])
        return wlink
    ##################################

    elif x[0] == 'if':             # (if test conseq alt)
        if len(x) == 4:
            (_, test, conseq, alt) = x
        elif len(x) == 3:
            (_, test, conseq) = x
            alt = None
        if eval(test, env):
            return eval(conseq, env)
        elif alt:
            return eval(alt, env)

    elif x[0] == 'set!':           # (set! var exp)
        (_, var, exp) = x
        env.find(var)[var] = eval(exp, env)
    elif x[0] == 'setparam':
        (_, param, value) = x
        try:
            env.parameters[param] = env.find(value)[value]
        except:
            env.parameters[param] = value
    elif x[0] == 'define':         # (define var exp)
        (_, var, exp) = x
        try:
            env[var] = eval(exp, env)
        except Exception as e:
            logger.warning('Failed to evaluate definition of "{}": {}'.format(var, e))
            logger.debug(traceback.format_exc())
            env[var] = None
    elif x[0] == 'sort':
        seq = [link for link in eval(x[1], env) if link is not None and link.output]
        logger.debug(seq)
        if len(seq) == 1: return seq
        try: pred = x[2]
        except: pred = '<'
        try:
            k = x[3]
            assert k == ':key'
            lam = x[4]
            eval(['define', 'sort_func', lam], env)
        except: lam = None
        rev = pred == '>'
        if lam:
            l = sorted(seq, key=lambda n: eval(['sort_func', n], env), reverse=rev)
        else:
            l = sorted(seq, reverse=rev)
        return l
    elif x[0] == 'lambda':         # (lambda (var*) exp)
        (_, vars, exp) = x
        return lambda *args: eval(exp, Env(vars, args, env))
    elif x[0] == 'upload':          # (upload exp) Store each intermediate for return
        (_,  exp) = x
        try:
            val = eval(exp, env)
            results = val
        except Exception as e:
            logger.warn('Failed to evaluate upload of "{}": {}'. format(to_string(exp), e))
            logger.debug(traceback.format_exc())
            env.errors.append(e)
            env.exceptions.append(traceback.format_exc())
            results = None
        if type(results) is list:
            for r in results:
                env.emissions.append(r)
        elif results:
            env.emissions.append(results)
        return results

    elif x[0] == 'get':
        (_, key, exp) = x
        chain = eval(exp, env)
        assert type(chain) is WaspLink
        val = chain.get_value(key)
        if isinstance(val, asmtypes.FileSet):
            chain['default_output'] = val
            return chain
        else: # A value
            return val
    elif x[0] == 'all_files': ## Gets all data from module directory
        (_, exp) = x
        chain = eval(exp, env)
        assert type(chain) is WaspLink
        all_files = utils.ls_recursive(chain['outpath'])
        module = chain['module']
        chain['default_output'] = asmtypes.set_factory('misc', all_files,
                                                       name='{}.all_files'.format(module),
                                                       keep_name=True)
        return chain
    elif x[0] == 'tar': ## Tar outputs from WaspLink(s)
        bare_exp, kwargs = extract_kwargs(x)
        wlinks = [eval(exp, env) for exp in bare_exp[1:]]

        ### Format tarball name
        if 'name' in kwargs:
            tar_name = '{}.tar.gz'.format(kwargs['name'])
        else: # Generate Tar Name
            tar_name = '{}.tar.gz'.format('_'.join([w['module'] for w in wlinks]))

        ### Tag the tarball fileset
        tag = kwargs.get('tag')
        tags = [tag] if tag else []

        ### Create new link
        chain = WaspLink('tar', wlinks)
        filelist = []
        for w in wlinks:
            filelist += w.files
        chain['default_output'] = asmtypes.set_factory(
            'tar', utils.tar_list(env.outpath, filelist, tar_name),
            name=tar_name, keep_name=True, tags=tags)
        return chain

    elif x[0] == 'begin':          # (begin exp*) Return each intermediate
        inner_env = Env(outer=env)
        val = []
        for exp in x[1:]:
            try:
                ret = eval(exp, inner_env)
                if ret:val.append(ret)
            except Exception as e:
                if list(e):
                    logger.warning('Failed to eval "{}": {}'.format(to_string(exp), e))
                    logger.debug(traceback.format_exc())
                    env.errors.append(e)
                    env.exceptions.append(traceback.format_exc())
        if val:
            return val if len(val) > 1 else val[0]

    elif x[0] == 'print':
        for exp in x[1:]:
            print eval(exp, env)

    elif x[0] == 'prog':          # same as begin, but use same env
        val = []
        for exp in x[1:]:
            try:
                ret = eval(exp, env)
                if ret: val.append(ret)
            except Exception as e:
                if list(e):
                    logger.warning('Failed to eval "{}": {}'.format(to_string(exp), e))
                    logger.debug(traceback.format_exc())
                    env.errors.append(e)
                    env.exceptions.append(traceback.format_exc())
        if val:
            return val if len(val) > 1 else val[0]


    else:                          # (proc exp*)
        exps = [eval(exp, env) for exp in x]
        proc = exps.pop(0)
        env.next_stage(x[0])
        try: ## Assembly functions
            return proc(*exps, env=env)
        except TypeError as e: ## Built-in functions
            logger.debug(traceback.format_exc())
            return proc(*exps)
################ parse, read, and user interaction

def extract_kwargs(exp):
    "Find :keys in top level exp"
    kwargs = {}
    stripped = []
    skip = False
    for i,x in enumerate(exp):
        if skip:
            skip = False
            continue
        if x[0] == ':':
            kwargs[x[1:]] = exp[i+1]
            skip = True
        else:
            stripped.append(x)
    return stripped, kwargs

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
        if val is not None:
            print to_string(val)

def run(exp, env):
    stages = 0
    for plugin in env.plugins:
        stages += exp.count(plugin)
    env.global_data['stages'] = stages
    return eval(parse(exp), env=env)


class WaspLink(dict):
    def __init__(self, module=None, link=None):
        self['link'] = link
        self['module'] = module
        self['default_output'] = ''
        self['data'] = None
        self['info'] = {}

    @property
    def files(self):
        """ Return default results of current link """
        out = self['default_output']
        if type(out) is list:
            return [f for fset in out for f in fset.files]
        return self['default_output'].files

    @property
    def output(self):
        return self['default_output']

    def insert_output(self, output, default_type, module_name):
        """ Parses the output dict of a completed module and stores the
        data and information within the WaspLink object """
        filesets = []
        for outtype, outvalue in output.items():
            name = '{}_{}'.format(module_name, outtype)
            if not type(outvalue) is list:
                outvalue = [outvalue]
            ## Store default output
            if default_type == outtype:
                if isinstance(outvalue[0], asmtypes.FileSet):
                    for out in outvalue:
                        out['tags'].append(module_name)
                    self['default_output'] = outvalue

                else: # Files
                    self['default_output'] = asmtypes.set_factory(outtype, [asmtypes.FileInfo(f) for f in outvalue],
                                                                  name=name)
                    self['default_output']['tags'].append(module_name)
            ## Store all outputs and values
            outputs = []
            are_files = False
            for out in outvalue:
                try:
                    if os.path.exists(out): # These are files, convert to FileInfo format
                        outputs.append(asmtypes.FileInfo(out))
                        are_files = True
                    else:
                        raise Exception('Not a file')
                except Exception as e: # Not a file
                    outputs = outvalue
                    break
            if are_files:
                filesets.append(asmtypes.set_factory(outtype, outputs, name=name))
            else:
                self['info'][outtype] = outputs if not len(outputs) == 1 else outputs[0]
        self['data'] = asmtypes.FileSetContainer(filesets)

    def get_value(self, key):
        if key in self['info']:
            return self['info'][key]
        return self['data'].find_type(key)[0]

    def traverse(self):
        if self['link']:
            logger.debug("traverse: {}".format(self['default_output']['name']))
            for i,wlink in enumerate(self['link']):
                logger.debug('link: {}'.format(i))
                wlink.traverse()

    def find_module(self, module):
        """ Traverses the chain to find module """
        if self['module'] == module:
            return self
        for wlink in self['link']:
            return wlink.find_module(module)

class WaspEngine():
    def __init__(self, plugin_manager, job_data, meta=None):
        self.constants_reads = 'READS'
        self.constants_contigs = 'CONTIGS'
        self.pmanager = plugin_manager
        self.assembly_env = add_globals(Env(job_data=job_data, meta=meta))
        self.assembly_env.update({k:self.get_wasp_func(k, job_data) for k in self.pmanager.plugins})
        self.assembly_env.plugins = self.pmanager.plugins
        self.job_data = job_data
        reads_link = WaspLink()
        contigs_link = WaspLink()
        if 'initial_data' not in job_data:
            job_data['initial_data'] = asmtypes.FileSetContainer(job_data.wasp_data().referencesets +
                                                                 job_data.wasp_data().readsets +
                                                                 job_data.wasp_data().contigsets)
        reads_link['default_output'] = list(job_data['initial_data'].readsets)
        contigs_link['default_output'] = list(job_data['initial_data'].contigsets)

        self.assembly_env.update({self.constants_reads: reads_link})
        self.assembly_env.update({self.constants_contigs: contigs_link})
        self.assembly_env.update({'arast_score': wf.arast_score,
                                  'has_paired': wf.has_paired,
                                  'has_short_reads_only': wf.has_short_reads_only,
                                  'n50': wf.n50})

    def run_expression(self, exp, job_data=None):
        if not job_data:
            job_data = self.job_data
        ## Run Wasp expression
        if type(exp) is str or type(exp) is unicode:
            w_chain = run(exp, self.assembly_env)
        ## Record results into job_data
        if type(w_chain) is not list: # Single
            w_chain = [w_chain]
        for w in self.assembly_env.emissions + w_chain:
            try:
                job_data.add_results(w['default_output'])
            except:
                logger.warn('Output not added: {}'.format(w))
        job_data['tracebacks'] = [str(e) for e in self.assembly_env.exceptions]
        job_data['errors'] = [str(e) for e in self.assembly_env.errors]
        return w_chain[0]

    def get_wasp_func(self, module, job_data):
         def run_module(*inlinks, **kwargs):
            # WaspLinks keep track of the recursive pipelines
             env = kwargs['env']
             ## Flatten inlinks if lists are present
             links = []
             for link in inlinks:
                 if type(link) is list:
                     links += link
                 else:
                     links.append(link)
             wlink = WaspLink(module, links)
             self.pmanager.run_proc(module, wlink, job_data, env.parameters)
             return wlink
         return run_module

###### Utility

def pipelines_to_exp(pipes, job_id):
    """
    Convert pipeline mode into Wasp expression
    """
    # Assume that these modules will use initial reads
    add_reads = ['sspace', 'reapr', 'bwa', 'bowtie2']

    all_pipes = []
    for pipe in pipes:
        exp = 'READS'
        params = []
        for m in pipe:
            if m[0] == '?':
                params.append(m[1:].split('='))
            else:
                if params:
                    setparams = ' '.join(['(setparam {} {})'.format(p[0], p[1]) for p in params])
                    exp = '(begin {} {})'.format(setparams, exp)
                    params = []
                if m in add_reads:
                    exp = '({} {} READS)'.format(m, exp)
                else:
                    exp = '({} {})'.format(m, exp)

        #### Flush params
        if params:
            setparams = ' '.join(['(setparam {} {})'.format(p[0], p[1]) for p in params])
            exp = '(begin {} {})'.format(setparams, exp)
            params = []

        #exp = '(upload {})'.format(exp)
        #all_pipes.append(exp)
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
            for n in get_orphans(pipe1):
                for m in get_orphans(pipe2):
                    if n == m and to_string(n) not in lces:
                        lce = to_string(n)
                        lces.add(lce)
                        replacements.append((lce.strip(), 'val{}'.format(val_num)))
                        defs.append('(define val{} {})'.format(val_num, lce.strip()))
                        val_num += 1

    #### Replace defined expressions
    for replacement in replacements:
        for i, pipe in enumerate(all_pipes):
            all_pipes[i] = pipe.replace(*replacement)

    #### Form final expression
    ranked_upload = '(upload (sort (list {}) > :key (lambda (c) (arast_score c))))'.format(' '.join(all_pipes))
    final_exp = '(begin {} (tar (all_files (quast {})) :name {}_analysis :tag quast))'.format(' '.join(defs), ranked_upload, job_id)
    return final_exp


def _has_sibling(exp_list, exp):
    if not exp_list:
        return False
    siblings = 0
    for e in exp_list:
        if type(e) is list:
            siblings += 1
    return exp in exp_list and siblings > 1

def orphans(exp_list, parent=None):
    for i,l in enumerate(exp_list):
        if type(l) is list:
            for e in orphans(l, parent=exp_list):
                yield e
        elif i == 0 and not _has_sibling(parent, exp_list):
            yield exp_list

def get_orphans(pipe_string):
    return [o for o in orphans(read_from(tokenize(pipe_string)))]
