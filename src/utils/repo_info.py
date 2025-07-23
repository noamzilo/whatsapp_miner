import os
import sys


def repo_root():
    if "REPO_ROOT" in os.environ:
        return os.environ["REPO_ROOT"]
    else:
        prev_location = sys.argv[0]
        start_location = os.path.abspath(os.path.dirname(sys.argv[0]))
        while start_location != prev_location:
            dir_content = os.listdir(start_location)
            if "version.py" in dir_content or ".git" in dir_content:
                return start_location
            else:
                prev_location = start_location
                start_location = os.path.dirname(start_location)
        return os.getcwd()


def repo_name():
    if "REPO_NAME" in os.environ:
        return os.environ["REPO_NAME"]
    else:
        return os.path.basename(repo_root())
