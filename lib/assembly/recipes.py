import sys
import os
from ConfigParser import SafeConfigParser

def parse(recipe):
    desc = ''
    rec = ''
    for line in recipe.strip().split('\n'):
        if line.rfind(';') != -1:
            desc += line[line.rfind(';')+1:].lstrip() + '\n'
        else:
            rec += line + '\n'
    return desc, rec

def get(rname, job_id=None):
    """ returns the recipe called RNAME """
    recipe = parse(getattr(sys.modules[__name__], 'recipes')[rname])[1]
    if job_id:
        return prefix_value(recipe, 'name', str(job_id))
    else:
        return recipe

def get_description(rname):
    """ returns the recipe description of RNAME """
    return parse(getattr(sys.modules[__name__], 'recipes')[rname])[0]

def get_all():
    all = {}
    for k,v in getattr(sys.modules[__name__], 'recipes').items():
        desc, recipe = parse(v)
        all[k] = {'description': desc, 'recipe': recipe}
    return all

def set_alias(target_recipe, alias):
    all = getattr(sys.modules[__name__], 'recipes')
    all.update({alias: all[target_recipe]})

def prefix_value(recipe, key, prefix):
    """
    Finds the value of the keyword and prefixes
    e.g. prefix_value('auto', 'name', job_id)
    (... :name analysis) ->  (... :name 42_analysis)
    """
    words = recipe.split()
    for i, word in enumerate(words):
        if word.find(':{}'.format(key)) != -1:
            return recipe.replace(words[i+1], '{}_{}'.format(prefix, words[i+1]))

def load_recipes():
    rootpath = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', '..'))
    default_recipe_path = "lib/assembly/recipes"

    # TODO: find a clean way to get the path to the configuration file
    # config = args.config
    # cparser = SafeConfigParser()
    # cparser.read(config)
    # recipe_path = cparser.get('compute', 'recipe_path') or default_recipe_path
    recipe_path = default_recipe_path

    if not os.path.isabs(recipe_path):
        recipe_path = os.path.join(rootpath, recipe_path)

    extension = ".lisp"
    for recipe_file in os.listdir(recipe_path):
        if recipe_file.endswith(extension):
            recipe_name = recipe_file[:-len(extension)]
            file_descriptor = open(recipe_path+ "/" + recipe_file)
            content = file_descriptor.read()
            file_descriptor.close()
            recipes[recipe_name] = content

    set_alias('faster', 'rast_fast')
    set_alias('fast', 'rast')
    set_alias('smart', 'rast_slow')

recipes = {}

# load recipes when the module is loaded.
load_recipes()
