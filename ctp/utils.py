from . import config

import os
import subprocess

def ensure_dir (dirpath):
    if not os.path.exists (dirpath):
        os.makedirs (dirpath)

def ensure_dir_for_file (filepath):
    ensure_dir (os.path.dirname (filepath))

VM_PREFIX = 'ctp-'
def id_from_vm_name (name):
    if not name.startswith (VM_PREFIX):
        raise ValueError ("{} VM name doesn't start with {}".format (name, VM_PREFIX))
    return int (name[len (VM_PREFIX):])

def run (*args):
    proc = subprocess.Popen (args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate ()
    retcode = proc.poll ()
    return retcode, stdout

def run_checked (*args):
    retcode, output = run (*args)
    if retcode:
        raise RuntimeError ('Error running "{}"'.format (' '.join (map (str, args))))
    return output

def ssh (vm, *command):
    return run (
        'ssh', 'core@localhost',
        '-p', str (vm.ssh),
        '-i', config.get_ssh_private_key_file (),
        '-o', 'StrictHostKeychecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        '-o', 'ConnectTimeout=1',
        '--', subprocess.list2cmdline (map (str, command))
    )

def ssh_checked (vm, *command):
    retcode, output = ssh (vm, *command)
    if retcode:
        raise RuntimeError ('Error running "{}" on ssh'.format (' '.join (map (str, command))))
    return output
