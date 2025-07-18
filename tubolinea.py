#!/usr/bin/env python3

import os, sys
import re
import subprocess
import time
import pickle

from multiprocessing import shared_memory,  resource_tracker, set_start_method
import logging

import argparse

PATH_MAX=255

# disattiva resource tracker, shm vengono chiuse manualmente
def ignore(*args, **kwargs):
    return

resource_tracker.register = ignore
resource_tracker.unregister = ignore
resource_tracker._CLEANUP_FUNCS = {}

# logga stdout e stderr del processo figlio
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)


template = """
import sys, pickle
from multiprocessing import shared_memory, resource_tracker

def ignore(*args, **kwargs):
    return

resource_tracker.register = ignore
resource_tracker.unregister = ignore
resource_tracker._CLEANUP_FUNCS = {}

class Func:
    def __call__(self, obj):
        return obj

def main():
    shm_arg_name = sys.argv[1]
    size = int(sys.argv[2])
    shm_return_pointer_name = sys.argv[3]

    shm_arg = shared_memory.SharedMemory(name=shm_arg_name)
    shm_return_pointer = shared_memory.SharedMemory(name=shm_return_pointer_name)


    data_bytes = shm_arg.buf[:size]
    obj = pickle.loads(data_bytes)
        
    f = Func()
    return_value = f(obj)

    data = pickle.dumps(return_value)
    shm_return_value = shared_memory.SharedMemory(create=True, size=len(data))
    shm_return_value.buf[:len(data)] = data

    name_bytes = shm_return_value.name.encode('utf-8')
    shm_return_pointer.buf[:len(name_bytes)] = name_bytes



if __name__ == "__main__":
    main()
"""

def instance_path(path: str):
    return f"{path}/__tubolinea__.py"

def retrieve_env(path: str):
    with open(instance_path(path), "r") as f:
        for line in f:
            match = re.match(r"#\s*env:\s*(\S+)", line)
            if match:
                return match.group(1)
    return ""

def create(path: str, env=""):
    with open(instance_path(path), "w") as f:
        # env retrieving metadata
        if env:
            f.write(f"# env:{env}\n")
        # template
        f.write(template)

def close_shm(*shm_list):
    for shm in shm_list:
        try:
            shm.close()
            shm.unlink()
        except:
            pass

def run(path: str, obj, env="", log_stdout=False, log_stderr=False):
    if env == "":
        env = retrieve_env(path)

    conda_cmd = ["conda", "run", "-n", env] if env else []

    try:

        data = pickle.dumps(obj)

        # shm_arg will host object to pass to the user defined function
        shm_arg = shared_memory.SharedMemory(create=True, size=len(data))
        # this is a buffer used to store the shared object name of the return value of the function
        shm_ptr = shared_memory.SharedMemory(create=True, size=PATH_MAX)

        shm_arg.buf[:len(data)] = data

        cmd = conda_cmd + ["python3", instance_path(path), shm_arg.name, str(len(data)), shm_ptr.name]

        proc = subprocess.run(
                cmd,
                capture_output=log_stdout
        )
        
        if log_stdout and proc.stdout:
            logging.info(f"{instance_path(path)}:\n%s", proc.stdout.decode())
        
        if log_stderr and proc.stderr:
            logging.error(f"{instance_path(path)}:\n%s", proc.stderr.decode())
        
        shm_return_name = shm_extract_path(shm_ptr)

        shm_return = shared_memory.SharedMemory(name=shm_return_name)
        return_data = bytes(shm_return.buf[:shm_return.size])

        close_shm(shm_arg, shm_ptr, shm_return)

        return pickle.loads(return_data)

    except:
        raise 

def shm_extract_path(shm):
    raw_bytes = bytes(shm.buf[:PATH_MAX])
    clean_bytes = raw_bytes.split(b'\x00', 1)[0]  # clean out all null chars
    return clean_bytes.decode('utf-8')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="at the moment the only subcommand is create")

    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="create a tubolinea instance")
    create_parser.add_argument("path", help="path where to install instance")
    create_parser.add_argument("--env", help="conda environment to use")

    args = parser.parse_args()

    if args.command == "create":
        if os.path.exists(instance_path(args.path)):
            risposta = input(f"overwrite {instance_path(args.path)}? (y/n): ").lower()
            if risposta != 'y':
                sys.exit(0)

        create(args.path, args.env)
