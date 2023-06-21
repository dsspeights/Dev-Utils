from ast import arg
from concurrent.futures.thread import _worker
from configparser import DEFAULTSECT
from email.policy import default
import imp
import json


import json
import yaml
from urllib import response
import os
import time

from datetime import date, datetime, timedelta

from constant import *
from DEFAULTS import DEFAULTS as DEFAULTS
from models import REMWork, create_default_from_dict, REManifest
from snippets import create_workspace_from_manifest, exec_this, exit_with_plog, include_which_elements, plog, prompt_for_input


def handle_verbosity(args: dict):
    """Wrapper to set initial verbosity if not included
    
    Args:
        args (dict): Command args
    
    Returns:
        dict: Command args, with updated verbosity
    """
    if not args.verbosity:
        args.verbosity = 1
    return args


def handle_setup(manifest: REManifest, args: dict):
    """Creates the needed plumbing for local use with defaults
    
    Args:
        rem (manifest): workspace manifest
        args (dict): Command args
    """
    plog(f"Running Setup for REM ... ", 0, args)
    git_user = prompt_for_input("GitHub User: ", "str", default="dsspeights")
    shell_file = prompt_for_input("Shell profile location: ", "str", default=f"{manifest.root}/.zshrc")
    reqs_file = prompt_for_input("Requirements location: ", "str", default=f"{manifest.rem}/requirements.txt")
    
    # Shell profile
    if os.path.isfile(shell_file):
        if prompt_for_input(f"Append `rem` alias to {shell_file}?", "str", default="N").upper() != "N":
            plog(f"Appending `rem` alias to {shell_file} ...", 0, args)
            exec_this(f"""echo "if [ -d ~/rem/ ]; then alias rem='python3 ~/rem/rem.py'; else echo 'ERR: Could not find rem in ~ ...'; fi" >> {shell_file} && source {shell_file}""")
    if prompt_for_input(f"Create {manifest.user_config}?", "str", default="N").upper() != "N":
        create = True
        if os.path.exists(manifest.user_config):
            create = prompt_for_input(f"Warning:  {manifest.user_config} exists!  Overwrite?", "str", default="N").upper() != "N"
        if create:
            plog(f"Creating {manifest.user_config} ...", 1, args)
            yaml_data = {
                'git': {
                    'user': git_user,
                },
                'shell': {
                    'profile': shell_file,
                }
            }
            with open(manifest.user_config, 'w') as yaml_config:
                yaml.dump(yaml_data, yaml_config)
    start_time = datetime.now()

    # Requirements
    if prompt_for_input(f"Install {reqs_file}?", "str", default="N").upper() != "N":
        try:
            plog(f"Installing {reqs_file} ... ", 1, args)
            exec_this(f"pip3 install -r {reqs_file}")
        except Exception as e:
            plog(f"{EXCEPTION_TEXT} {e}", 0, args)
    plog("Finished setup!", 0, args)
    plog(COMMAND_COMPLETE_TEXT + str(timedelta(0, (datetime.now() - start_time).seconds)), 1, args)


def handle_config_check(args: dict, config: str):
    """Runs os.path.exists against config path
    """
    plog(f"Checking for config {config} ... ", 2, args)
    if not os.path.exists(config):
        exit_with_plog(1, CONFIG_MISSING_TEXT + config, args)


def handle_lock_exists(args: dict, lock_file: str):
    """Runs os.path.exists against lock path
    """
    plog(f"Checking for lock file {lock_file} ... ", 2, args)
    if not os.path.exists(lock_file):
        exit_with_plog(1, LOCK_FILE_PRESENT_TEXT + lock_file, args)


def handle_create(manifest: REManifest, args: dict):
    """Wrapper that creates, propagates the new workspace
    """
    plog("Creating a new manifest ...", 1, args)
    handle_config_check(args, manifest.user_config)
    workspace = REMWork()
    try:
        # Release and config
        manifest.name = prompt_for_input("Enter workspace name: ", "str", default="latest")
        manifest.workspace = manifest.root + f"/{manifest.name}"
        manifest.config = manifest.workspace + YAML_FILE
        if os.path.exists(manifest.workspace):
            exit_with_plog(1, "ERROR: Workspace already exists!", args)
        # Check which defaults to include
        include_which_elements(manifest, args)
        # Create the workspace
        create_workspace_from_manifest(manifest, args)
    except KeyboardInterrupt:
        plog("\nExiting create!", 0, args) & exit(1)
    # except Exception as e:
    #     plog(EXCEPTION_TEXT + str(e), 0, args)
    plog("Finished create!", 0, args)
    workspace.end_time = datetime.now()
    plog(COMMAND_COMPLETE_TEXT + str(timedelta(0, (workspace.end_time - workspace.start_time).seconds)), 1, args)


def handle_destroy(manifest: REManifest, args:dict):
    """Perform a soft delete... What's that?
       1. create a (hidden) temp director
       2. do a (quick) move of the specified directory to the new (hidden) temp directory
       3. do a sleep to allow for reactionary reversions
       4. do a force remove of the (hidden) temp directory, in the background
    """
    plog("Starting delete ...", 0, args)
    handle_config_check(args, manifest.user_config)
    workspace = REMWork()
    # What are we destroying?
    workspace.where = f"{manifest.root}/{args.destroy}"
    if not os.path.exists(workspace.where):
        exit_with_plog(1, f"Error: Target '{workspace.where}' not found!", args)
    # Create a tmp place ...
    TMP_DIR = f"{manifest.root}/._cleanup_{args.destroy}"
    try:
        plog(f"Found '{workspace.where}'", 1, args)
        plog(f" ... moving workspace to tmp dir: {TMP_DIR}", 1, args)
        mv_cmd = f"mv {workspace.where} {TMP_DIR}"
        exec_this(mv_cmd)
        plog(f" ... starting background task to remove: {TMP_DIR}", 1, args)
        rm_cmd = f"{SOFT_DELETE_COMMAND} {TMP_DIR} &"
        exec_this(rm_cmd)
        plog(f" ... you have a limited amount of time to cancel the task before it runs: ", 2, args)
        exec_this("ps -ef | grep 'sleep 300 && rm -fr' | egrep -v 'grep'")
        plog(f" ... started: {rm_cmd} ... ", 1, args)
    except KeyboardInterrupt:
        plog("\nExiting destroy!", 0, args) & exit(1)
    plog("Finished destroy!", 0, args)
    workspace.end_time = datetime.now()
    plog(COMMAND_COMPLETE_TEXT + str(timedelta(0, (workspace.end_time - workspace.start_time).seconds)), 1, args)


def handle_update(manifest: REManifest, args: dict):
    """Rebase and merge local changes with the latest from upstream
    """
    plog("Starting update ...", 0, args)
    handle_config_check(args, manifest.user_config)
    workspace = REMWork()
    manifest.name = args.update
    manifest.workspace = f"{manifest.root}/{manifest.name}"
    manifest.config = str(manifest.workspace) + YAML_FILE
    workspace.lock_file = str(manifest.workspace) + LOCK_FILE
    os.chdir(manifest.workspace)
    handle_config_check(args, manifest.config)
    handle_lock_exists(args, workspace.lock_file)
    try:
        with open(manifest.config) as new_manifest:
            json_data = yaml.safe_load(new_manifest)
            plog(f"Workspace name: {json_data['name']}", 1, args)
        
        for data in json_data['elements']:
            element = create_default_from_dict(json_data['elements'][data])
            if not element.name or not os.path.exists(f"{manifest.workspace}/{element.name}"):
                plog(f"Skipping '{element.name}', target values/path not found in {manifest.workspace}", 1, args)
            else:
                workspace.where = f"{manifest.workspace}/{element.name}"
                if element.origin and element.default_branch:
                    log_data = {
                        "update": element.name,
                        "cmd": f"git fetch upstream master ; git pull upstream {element.default_branch} --rebase ; git merge upstream/{element.default_branch}",
                        "started": datetime.now().strftime("%D @ %H:%M:%S")
                    }
                    with open(workspace.lock_file, 'w') as lockfile:
                        json.dump(log_data, lockfile)
                    os.chdir(workspace.where)
                    try:
                        exec_this("git status .")
                        plog(f"Executing: {log_data['cmd']}", 1, args)
                        response = exec_this(f"{log_data['cmd']}")
                        plog(f"Response: {response}", 1, args)
                    except Exception as e:
                        plog(f"ERROR: Exception raised during update: {e}", 0, args)
                    plog(f"Finished updating {element.name} ... ", 1, args)
                    os.chdir(manifest.workspace)
                    plog("Removing lockfile ... ", 1, args)
                    now = datetime.now().strftime("%Y_%m_%d")
                    exec_this(f"cat {workspace.lock_file} >> {manifest.workspace}/.updatelog_{now}")
                    time.sleep(3)
                    os.remove(workspace.lock_file)
    except KeyboardInterrupt:
        plog("\nExiting update!", 0, args) & exit(1)
    except Exception as e:
        plog(f"{EXCEPTION_TEXT} {e}", 0, args)
    plog("Finished update!", 0, arg)
    workspace.end_time = datetime.now()
    plog(COMMAND_COMPLETE_TEXT + str(timedelta(0, (workspace.end_time - workspace.start_time).seconds)), 1, args)


def handle_print_commands(manifest: REManifest, args: dict):
    """Print all workspace commands, from config
    """
    plog("Starting print workspace props ... ", 0, args)
    handle_config_check(args, manifest.user_config)
    workspace = REMWork()
    os.chdir(manifest.workspace)
    manifest.name = args.print
    manifest.workspace = f"{manifest.root}/{manifest.name}"
    manifest.config = str(manifest.workspace) + YAML_FILE
    workspace.lock_file = str(manifest.workspace) + LOCK_FILE
    try:
        with open(manifest.config) as release_manifest:
            json_data = yaml.safe_load(release_manifest)
            plog(f"Workspace name: {json_data['name']}", 1, args)
        
        for data in json_data['elements']:
            plog(f"Elements: ", 1, args)
            element = create_default_from_dict(json_data['elements'][data])
            for prop in element.get_props():
                print(f"    {prop.capitalize()}:")
                if json_data['elements'][data][prop] and isinstance(json_data['elements'][data][prop], list):
                    for each in json_data['elements'][data][prop]:
                        print(f"    {each}")
                elif json_data['elements'][data][prop]:
                    print(f"    {json_data['elements'][data][prop]}")
    except KeyboardInterrupt:
        plog("\nExiting print workspace properties", 0, args) & exit(1)
    except Exception as e:
        plog(f"{EXCEPTION_TEXT} {e}", 0, args)
    plog("Finished print workspace properties!", 0, args)
    workspace.end_time = datetime.now()
    plog(COMMAND_COMPLETE_TEXT + str(timedelta(0, (workspace.end_time - workspace.start_time).seconds)), 1, args)
    

def handle_commands(manifest: REManifest, args: dict, command: str):
    """Generic wrapper for executing commands
    """
    plog(f"Starting {command.title()} ... ", 0, args)
    handle_config_check(args, manifest.user_config)
    workspace = REMWork()
    # Set the release and config
    manifest.name = getattr(args, command)
    manifest.workspace = f"{manifest.root}/{manifest.name}"
    manifest.config = str(manifest.workspace) + YAML_FILE
    workspace.lock_file = str(manifest.workspace) + LOCK_FILE
    os.chdir(manifest.workspace)
    # config?
    handle_config_check(args, manifest.config)
    handle_lock_exists(args, workspace.lock_file)
    try:
        # get props
        with open(manifest.config) as workspace_manifest:
            json_data = yaml.safe_load(workspace_manifest)
            manifest.name = json_data['name']
            manifest.workspace = json_data['workspace']
            manifest.rem = json_data['rem']
            manifest.elements = json_data['elements']
        plog(f"Workspace name: {json_data['name']}", 1, args)
        plog(f"Elements: {manifest.elements}", 2, args)
        # For each element, find and execute the command(s)
        for data in workspace.elements:
            element = create_default_from_dict(manifest.elements[data])
            workspace.where = f"{manifest.workspace}/{element.name}"
            if not element.name or not os.path.exists(workspace.where):
                plog(f"Skipping '{element.name}', target values/path not found in {manifest.workspace}", 1, args)
                continue
            log_data = {
                "type": "build",
                "name": element.name,
                "cmds": getattr(element, command),
                "started": datetime.now().strftime("%D @ %H:%M:%S")
            }
            with open(workspace.lock_file, 'w') as lock:
                json.dump(log_data, lock)
            if not log_data["cmds"]:
                plog(f"Skipping {command} on {element.name} ...", 2, args)
            else:
                plog(f"Starting {command} on {element.name} via {log_data['cmds']} ...", 1, args)
                time.sleep(3)
                if type(log_data["cmds"]) == list:
                    for cmd in log_data["cmds"]:
                        os.chdir(workspace.where)
                        plog("WHERE AM I ... ", 2, args)
                        plog(exec_this('pwd'), 2, args)
                        plog(f"Executing {command} cmd: '{cmd}' ... ", 1, args)
                        exec_this(cmd)
                        time.sleep(5)
                else:
                    os.chdir(workspace.where)
                    plog("WHERE AM I ... ", 2, args)
                    plog(exec_this('pwd'), 2, args)
                    plog(f"Executing {command} cmds: '{log_data['cmds']}' ... ", 1, args)
                    exec_this(log_data['cmds'])
                    time.sleep(5)
            plog(f"Finished {command} on {element.name} ... ", 1, args)
            os.chdir(manifest.workspace)
            plog("Removing LOCK ...", 1, args)
            now = datetime.now().strftime("%Y_%m_%d")
            exec_this(f"cat {workspace.lock_file} >> {manifest.workspace}/.{command}_log_{now}")
            time.sleep(5)
            os.remove(workspace.lock_file)
    except KeyboardInterrupt:
        plog("\nExiting!", 0, args) & exit(1)
    except Exception as e:
        plog(f"{EXCEPTION_TEXT} {e}", 0, args)
    plog(f"Finished {command.title()}!", 1, args)
    workspace.end_time = datetime.now()
    plog(COMMAND_COMPLETE_TEXT + str(timedelta(0, (workspace.end_time - workspace.start_time).seconds)), 1, args)


def handle_args(manifest: REManifest, args):
    """Wrapper to gracefully handle, in the desired order, args
    """
    plog(f"Checking args: {args} ...", 2, args)
    for arg in args.__dict__:
        if args.__dict__[arg]:
            plog(f"Checking arg: {arg} ", 2, args)
            # These are special use cases, executing the same command regardless of the workspace
            if arg == 'verbosity':
                continue # already handled
            if arg == 'setup':
                handle_setup(manifest, args)
            elif arg == 'create':
                handle_create(manifest, args)
            elif arg == 'update':
                handle_update(manifest, args)
            elif arg == 'destroy':
                handle_destroy(manifest, args)
            elif arg == 'print':
                handle_print_commands(manifest, args)
            # otherwise, check for an argparse value
            else:
                handle_commands(manifest, args, arg)

