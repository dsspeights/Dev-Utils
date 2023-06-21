import confuse
import os

from constant import USER_YAML_FILE
from models import REMDefault

# Load the yaml
try:
    config = confuse.Configuration('REM', __name__)
    config.set_file(os.path.expanduser("~") + USER_YAML_FILE)
    
    GIT_USER = config['git']['user'].get(str)
    #SHELL_FILE = config['zsh']['profile'].get(str)

except confuse.exceptions.ConfigReadError:
    GIT_USER = ""
except confuse.exceptions.NotFoundError:
    GIT_USER = ""

# Collecting defaults

DEFAULTS = [REMDefault(
    name="bible_databases",
    clone="https://github.com/scrollmapper/bible_databases",
    upstream="https://github.com/scrollmapper/bible_databases",
    origin="https://github.com/{GIT_USER}/bible_databases",
    default_branch="master"
)]

DEFAULTS.append(REMDefault(
    name="bible_databases_deuterocanonical",
    clone="https://github.com/scrollmapper/bible_databases_deuterocanonical",
    upstream="https://github.com/scrollmapper/bible_databases_deuterocanonical",
    origin="https://github.com/{GIT_USER}/bible_databases_deuterocanonical",
    default_branch="master"
))