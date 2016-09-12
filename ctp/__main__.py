from . import create
from . import mount
from . import debug
from .errors import CTPError

import argparse
import getpass
import os
import sys
import functools

def mount_command ():
    parser = argparse.ArgumentParser ()
    parser.add_argument ('crypt', nargs='?')
    args = parser.parse_args ()

    if not args.crypt:
        mount.list_mounts ()
        return

    if not os.path.exists (args.crypt):
        parser.error ('No crypt file found')

    try:
        ask_for_password = functools.partial (getpass.getpass, 'Enter crypt password: ')
        password = ask_for_password ()
        mount_point = '/tmp/ctp/' + os.path.basename (args.crypt)
        mount.mount (args.crypt, mount_point, password, password_callback=ask_for_password)
    except CTPError as e:
        print ('Error:', e, file=sys.stderr)
    except KeyboardInterrupt:
        pass

def umount_command ():
    parser = argparse.ArgumentParser ()
    parser.add_argument ('crypt')
    args = parser.parse_args ()

    try:
        mount.unmount (args.crypt)
    except CTPError as e:
        print ('Error:', e, file=sys.stderr)
    except KeyboardInterrupt:
        pass

def create_command ():
    parser = argparse.ArgumentParser ()
    parser.add_argument ('-s', '--size-mb', type=int, required=True)
    parser.add_argument ('crypt')
    args = parser.parse_args ()

    if args.size_mb <= 10:
        parser.error ('Size is too small')
    elif os.path.exists (args.crypt):
        parser.error ('Crypt exists')

    try:
        password = getpass.getpass ("Enter new password for crypt: ")
        if not password:
            raise CTPError ('Password is empty')
        if password != getpass.getpass ("Repeat password: "):
            raise CTPError ("Passwords don't match")

        create.create (args.crypt, args.size_mb, password)
    except CTPError as e:
        print ('Error:', e, file=sys.stderr)
    except KeyboardInterrupt:
        pass

def debug_command ():
    parser = argparse.ArgumentParser ()
    parser.add_argument ('crypt')
    args = parser.parse_args ()

    if not os.path.exists (args.crypt):
        parser.error ('No crypt file found')

    debug.debug (args.crypt)
