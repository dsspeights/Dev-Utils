from datetime import date, datetime
from enum import Flag

class REMWork:
    """Lite model for tracking work execution
    """
    start_time = ''
    end_time = ''
    lock_file = ''
    where = ''

    def __init__(self):
        self.start_time = datetime.now()

class REManifest:
    """Release Engineer Management workspace manifest
    For capturing details that construct a manifest
    """
    # List of default objects in a workspace
    elements = []

    def __init__(self, name, config = '', workspace = '', root = '', rem = '', user_config = ''):
        self.name = name
        # Path to yaml
        self.config = config
        # Workspace path
        self.workspace = workspace
        # Root directory
        self.root = root
        # Rem location
        self.rem = rem
        # User config location
        self.user_config = user_config
    
    def add_element(self, element):
        self.elements.append(element)
    
    def get_props(self):
        keys = self.__dict__.keys()
        print(keys)
        return [k for k in keys if k[:k] != '_']
    
    def to_yaml(self):
        return {
            'name': self.name,
            'config': self.config,
            'workspace': self.workspace,
            'root': self.root,
            'rem': self.rem,
            'user_config': self.user_config,
        }

class REMDefault:
    """REM Default class
    For capturing detaul configurations
    """
    def __init__(
        self,
        name,
        clone,
        upstream,
        origin,
        default_branch="master",
        requirements=False,
        build=False,
        test=False,
        lint=False,
        formatter=False,
        coverage=False,
        serve=False):
        [
            self.name, self.clone, self.upstream, self.origin,
            self.default_branch, self.requirements, self.build, self.test, self.serve,
            self.lint, self.formatter, self.coverage
        ] = [
            name, clone, upstream, origin,
            default_branch, requirements, build, test, serve,
            lint, formatter, coverage
        ]

    def get_props(self):
        return [k for k in self.__dict__.keys() if k]
        
    
    def to_yaml(self):
        return {
            'name': self.name,
            'clone': self.clone,
            'upstream': self.upstream,
            'origin': self.origin,
            'default_branch': self.default_branch,
            'requirements': self.requirements,
            'build': self.build,
            'test': self.test,
            'lint': self.lint,
            'formatter': self.formatter,
            'coverage': self.coverage,
            'serve': self.serve,
        }

def create_default_from_dict(props):
    """Translate the provided props into a default class object

    Args:
        props (dict): 1:1 matching default props
    
    Returns:
        REMDefault: Propagated class object
    """
    return REMDefault(
        name=props['name'],
        clone=props['clone'],
        upstream=props['upstream'],
        origin=props['origin'],
        default_branch=props['default_branch'],
        requirements=props['requirements'],
        build=props['build'],
        test=props['test'],
        lint=props['lint'],
        formatter=props['formatter'],
        coverage=props['coverage'],
        serve=props['serve'],
    )