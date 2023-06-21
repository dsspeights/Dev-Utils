#!/usr/bin/env python3
import argparse
import json
import logging
import os

from constant import EXCEPTION_TEXT, USER_YAML_FILE
from handlers import handle_args, handle_verbosity
from models import REManifest
from snippets import exit_with_plog, validate

def main(manifest: REManifest):
    """
    """
    logging.info("Started")

    parser = argparse.ArgumentParser(
        description="Tooling for rapidly creating, updating, building and testing (multi-)SCM-based workspaces.",
        epilog="Better engineer the world you've been temporarily gifted domain ..."
    )
    parser.add_argument("-C", "--create", action="store_true", help="Create a new workspace")
    parser.add_argument("-D", "--destroy", type=str, help="Destroy the specified workspace")
    parser.add_argument("-P", "--print", type=str, help="Print the specified workspace's various commands")
    parser.add_argument("-S", "--setup", action="store_true", help="Setup")
    parser.add_argument("-U", "--update", type=str, help="Update")
    parser.add_argument("-v", "--verbosity", type=int, choices=[0,1,2], help="Increase verbosity")
    parser.add_argument("-b", "--build", type=str, help="Build the workspace")
    parser.add_argument("-c", "--coverage", type=str, help="Check code coverage")
    parser.add_argument("-f", "--formatter", type=str, help="Check code formatting")
    parser.add_argument("-s", "--serve", type=str, help="Lint the workspace")
    parser.add_argument("-t", "--test", type=str, help="Test the workspace")

    try:
        args = validate(parser)
    except Exception as e:
        parser.print_help()
        exit_with_plog(1, EXCEPTION_TEXT + str(e), args)
    
    args = handle_verbosity(args)
    handle_args(manifest, args)

if __name__ == '__main__':
    """
    """
    manifest = REManifest("REM")
    manifest.rem = os.path.dirname(os.path.realpath(__file__))
    manifest.root = os.path.expanduser("~")
    manifest.user_config = manifest.root + USER_YAML_FILE
    main(manifest)
