import os
import subprocess

def ensure_dir_for_file (filepath):
    if not os.path.exists (os.path.dirname (filepath)):
        os.makedirs (os.path.dirname (filepath))

VM_PREFIX = 'ctp-'
def id_from_vm_name (name):
    if not name.startswith (VM_PREFIX):
        raise ValueError ("{} VM name doesn't start with {}".format (name, VM_PREFIX))
    return int (name[len (VM_PREFIX):])

def run (*args):
    proc = subprocess.Popen (args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, _ = proc.communicate ()
    retcode = proc.poll ()
    return retcode, output

def run_checked (*args):
    retcode, output = run (*args)
    if retcode:
        raise RuntimeError ('Error running "{}"'.format (''.join (args)))
    return output
