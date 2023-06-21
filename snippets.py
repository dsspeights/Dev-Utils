from ctypes import Union
import datetime
import os, sys
import json
from typing import Iterable, Sequence
import yaml
from unittest import result
import shutil

from constant import LOG_FORMAT
from DEFAULTS import DEFAULTS as DEFAULTS
from models import create_default_from_dict, REManifest

def plog(text: str, level: int, args: dict):
    """Print text to the specified log level
    """
    tstamp = datetime.datetime.now().strftime(LOG_FORMAT)
    if not args.verbosity:
        print(f"{tstamp} Out - {text}")
    else:
        if level > 1:
            if args.verbosity > 1:
                print(f"{tstamp} DEBUG - {text}")
        elif level > 0:
            if args.verbosity > 0:
                print(f"{tstamp} Info - {text}")
        else:
            print(f"{tstamp} - {text}")

def exit_with_plog(code: int, msg: str, args: dict):
    """Wrapper for plog, with exit-ability
    """
    plog(f"{msg}", 1, args)
    exit(code)

def validate(parser):
    """Validate REM configuration
    """
    args = parser.parse_args()
    if len(sys.argv) <= 1:
        exit_with_plog(1, "Warning - Expected args ... see usage '-h'", args)
    return args

def prompt_for_input(prompt: str, input_type: str, default: str):
    """Prompt for user input, return the result
    """
    print(f"    {prompt}", end='')
    if default:
        print(f" (default: {default}) ", end='')
    waiting_for_input = True
    result = False
    while waiting_for_input:
        if input_type == "int":
            result = int(input())
        elif input_type == "str":
            result = str(input())
        elif input_type == "bool":
            result = bool(input())
        if not result:
            if default:
                result = default
                waiting_for_input = False
            else:
                print(f"Warning: Invalid input, expected {input_type}")
        else:
            waiting_for_input = False
    return result
                
def exec_this(cmd: str, stdout: str = ''):
    """Execute the specified command, wrapper for os.system()
    """
    return os.system(cmd + stdout)

def create_manifest_elements(manifest: REManifest, args: dict):
    """Create each element specified in the manifest
    """
    for element in manifest.elements:
        element_path = manifest.workspace + f'/{element.name}'
        plog(f"Creating element: {element.name} ... ", 0, args)
        try:
            os.chdir(manifest.root)
            if not element.requirements:
                plog("Skipping requirements validation ... ", 1, args)
            else:
                plog("Validate requirements ...", 1, args)
                plog(f"Element requirements: {element.requirements} ", 2, args)
                for requirement in element.requirements:
                    plog(f"Validate: '{requirement}' ... ", 2, args)
                    result = exec_this(requirement, ' 1>/dev/null')
                    if result != 0:
                        plog(f"FAILED validate requirement: \n'{requirement}'\n ... exit code: {result}", 0, args)
                        plog(f"Force CLEANUP workspace: '{manifest.workspace}' ... ", 2, args)
                        shutil.rmtree(manifest.workspace, ignore_errors=True)
                        exit_with_plog(3, "Finished cleanup!", args)
            # Clone
            plog(f"Cloning {element.name} into {element_path} ... ", 1, args)
            git_cmd = f"git clone {element.clone} {element_path}"
            exec_this(git_cmd)
            plog(f"Changing directories into clone {element_path}", 2, args)
            os.chdir(element_path)
            # Set remotes
            git_cmd = "git remote -v"
            git_cmd_1 = "git remote remove origin"
            git_cmd_2 = f"git remote add upstream {element.upstream}"
            git_cmd_3 = f"git remote add origin {element.origin}"
            plog("Setting remotes ... currently: ", 1, args)
            exec_this(git_cmd)
            plog("Removing origin ... ", 1, args)
            exec_this(git_cmd_1)
            plog(f"Setting upstream to {element.upstream} ... ", 2, args)
            exec_this(git_cmd_2)
            plog(f"Setting origin to {element.origin} ... ", 2, args)
            exec_this(git_cmd_3)
            plog("Done setting remotes: ", 2, args)
            exec_this(git_cmd)
            # Set branch
            plog("Checking branches ... currently: ", 1, args)
            exec_this("git branch -v")
            if element.default_branch == 'master':
                plog(f"No changes, branch already set to origin/{element.default_branch} ... ", 2, args)
            else:
                plog("Fetching remote branches ... ", 2, args)
                exec_this("git fetch")
                plog(f"Setting branch to origin/{element.default_branch} ... ", 1, args)
                exec_this(f"git checkout -t origin/{element.default_branch}")
                plog("Ending branches: ", 1, args)
                exec_this("git branch -v")
            os.chdir(manifest.root)
            plog(f"Fiished {element.name} ... ", 1, args)
        except KeyError:
            plog(f"Skiping {element.name} ... ", 2, args)
            return
        except Exception as e:
            plog(f"WARNING: create_this_element raised Exception {e} ", 0, args)

def create_workspace_from_manifest(manifest: REManifest, args: dict):
    """Create the workspace location, config and kick off manifest element creation
    """
    elements = []
    if not manifest.elements:
        exit_with_plog(1, "No elements selected!", args)
    else:
        for element in manifest.elements:
            elements.append(element)
    # Get in place
    exec_this("cd " + str(manifest.root))
    # Create the directory
    if not os.path.exists(manifest.workspace):
        plog(f"Creating {manifest.workspace} ... ", 1, args)
        exec_this(f"mkdir {manifest.workspace}")
    else:
        exit_with_plog(1, f"Workspace {manifest.workspace} exists!", 1, args)

    # Create config
    if not os.path.exists(manifest.config):
        plog(f"Creating {manifest.config} ... ", 1, args)
        yaml_data = manifest.to_yaml()
        yaml_data['elements'] = dict()
        for element in manifest.elements:
            yaml_data['elements'][element.name] = element.to_yaml()
        with open(manifest.config, 'w') as rem_config:
            yaml.dump(yaml_data, rem_config)
    
    # Create/clone elements
    plog("Checking elements ... ", 0, args)
    create_manifest_elements(manifest, args)
    plog("Finished!", 1, args)

def include_which_elements(manifest: REManifest, args: dict):
    """Sequentiall prompt user for which element(s) to include from defaults
    """
    # Determine configurations ...
    for element in DEFAULTS:
        # Include?
        plog(f"Checking element.name: {element.name} ... ", 2, args)
        if prompt_for_input(f"Include {element.name}? ", "str", default="N").upper() != "N":
            DEFAULT = True if prompt_for_input(f"   Use defaults for: {element.name}?", "str", default="Y").upper() == "Y" else False
            if not DEFAULT:
                exit_with_plog(1, "TBA", args)
            else:
                plog(f"Using defaults for {element.name}", 2, args)
                props = {}
                for prop in element.get_props():
                    props[prop] = getattr(element, prop)
                default = create_default_from_dict(props)
                manifest.add_element(default)
