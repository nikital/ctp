import utils
import errors

import shelve
import contextlib
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

@contextlib.contextmanager
def _state_shelve ():
    s = shelve.open (user_path ('state'), writeback=True)
    if 'mounts' not in s:
        s['mounts'] = {}
    yield s
    s.close ()

def set_mount (mount, vm, mount_point = None):
    mount = os.path.realpath (mount)
    with _state_shelve () as s:
        s['mounts'][mount] = (vm, mount_point)

def get_mount (mount):
    mount = os.path.realpath (mount)
    with _state_shelve () as s:
        if mount not in s['mounts']:
            raise errors.CTPError ('Location {} not mounted'.format (mount))
        return s['mounts'][mount]

def get_all_mounts ():
    with _state_shelve () as s:
        return s['mounts']

def verify_no_mount (mount):
    mount = os.path.realpath (mount)
    with _state_shelve () as s:
        if mount in s['mounts']:
            raise errors.CTPError ('Location {} already mounted'.format (mount))

def remove_mount (mount):
    mount = os.path.realpath (mount)
    with _state_shelve () as s:
        del s['mounts'][mount]

@contextlib.contextmanager
def mount_context (mount, vm = None, mount_point = None):
    set_mount (mount, vm, mount_point)
    yield
    remove_mount (mount)
