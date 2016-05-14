import utils

import os

USER_CONFIG_DIR = os.path.expanduser ('~/.config/ctp/')

def user_path (path):
    return USER_CONFIG_DIR + path

def _gen_ssh_key ():
    # TODO(nik) kill all existing VMs when we change the key
    utils.run_checked ('ssh-keygen', '-N', '', '-f', user_path ('ssh'))

def get_ssh_private_key_file ():
    target = user_path ('ssh')
    if not os.path.exists (target):
        _gen_ssh_key ()
    return target

def get_ssh_public_key_file ():
    target = user_path ('ssh.pub')
    if not os.path.exists (target):
        _gen_ssh_key ()
    return target

def get_ssh_public_key ():
    with open (get_ssh_public_key_file (), 'r') as f:
        return f.read ().strip ()
