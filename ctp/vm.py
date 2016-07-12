import config
import utils
from errors import CTPError

import os
import shutil
import sys
import tempfile
import urllib
import contextlib
import itertools
import time

DISK_URL = 'https://stable.release.core-os.net/amd64-usr/current/coreos_production_virtualbox_image.vmdk.bz2'
PORT_BASE = 11100

def aquire_vm (disk=None):
    '''Returns a fresh, ready to use, powered on VM'''

    # Find unused VM
    powered_on = list (i.split('"')[1] for i in _vbox_manage ('list', 'runningvms').splitlines ())
    for vm_index in itertools.count ():
        vm_name = 'ctp-{}'.format (vm_index)
        if vm_name not in powered_on:
            break

    machine = VM (vm_name)
    if disk is not None:
        machine.attach_disk (disk)
    machine.poweron ()
    return machine

def attach_vm (name, disk=None):
    '''Returns an already running VM, by name.'''
    machine = VM (name)
    if not machine.is_powered_on ():
        raise CTPError ('The VM is not running')
    machine.disk = disk
    return machine

def release_vm (machine):
    machine.poweroff ()

@contextlib.contextmanager
def vm_context (disk=None):
    machine = aquire_vm (disk)
    yield machine
    release_vm (machine)

def create_medium (path, size):
    if os.path.exists (path):
        raise CTPError ('VDI already exists at {}'.format (path))
    # This is unchecked because VBox may err even if the creation was
    # successful but it couldn't register the volume because a
    # different volume was registered for the same path
    _vbox_manage_unchecked (
        'createmedium', 'disk',
        '--filename', path,
        '--size', size,
    )
    if not os.path.exists (path):
        raise CTPError ('Failed to create VDI at {}'.format (path))

def _print_progress (blocks, block_size, total_size):
    percent = 1.0 * blocks * block_size / total_size
    sys.stdout.write ('\r{:3.0f}% [{:50}] '.format (percent * 100, int (50 * percent) * '='))
    sys.stdout.flush ()

def _get_coreos_disk ():
    target = config.user_path ('vm/disk/coreos.vmdk')
    target_bz2 = target + '.bz2'
    if os.path.exists (target):
        return target

    utils.ensure_dir_for_file (target)

    print 'Downloading CoreOS disk'
    sys.stdout.write ('Initializing connection...')
    sys.stdout.flush ()
    filename, headers = urllib.urlretrieve (DISK_URL, reporthook=_print_progress)
    shutil.move (filename, target_bz2)

    print 'Decompressing CoreOS disk...'
    utils.run_checked ('bunzip2', target_bz2)
    print 'Done.'

    return target

def _get_cloudconfig ():
    target = config.user_path ('vm/disk/ctp-cloudconfig.iso')
    if os.path.exists (target):
        return target

    utils.ensure_dir_for_file (target)
    volume = tempfile.mkdtemp ()
    user_data_path = volume + '/openstack/latest/user_data'
    utils.ensure_dir_for_file (user_data_path)

    with open (user_data_path, 'w') as f:
        f.write ('#cloud-config\n\n')
        f.write ('ssh_authorized_keys:\n')
        f.write (' - {}\n'.format (config.get_ssh_public_key ()))
        f.write ('write_files:\n')
        f.write (' - content: /mnt 0.0.0.0/1(rw,sync,insecure,no_subtree_check,all_squash,anonuid=0,anongid=0)\n')
        f.write ('   path: /etc/exports\n')
        f.write ('coreos:\n')
        f.write (' units:\n')
        f.write ('  - name: nfs-server.service\n')
        f.write ('    command: start\n')
        f.write ('  - name: nfs-mountd.service\n')
        f.write ('    drop-ins:\n')
        f.write ('     - name: 10-set-port.conf\n')
        f.write ('       content: |\n')
        f.write ('        [Service]\n')
        f.write ('        Environment="RPCMOUNTDARGS=-p 11111"\n')

    print 'Creating cloud-config'
    utils.run_checked ('hdiutil', 'makehybrid', '-iso', '-joliet',
                 '-default-volume-name', 'config-2',
                 '-o', target,
                 volume,
    )
    return target

def _vbox_manage (*args):
    return utils.run_checked ('VBoxManage', *map (str, args))

def _vbox_manage_unchecked (*args):
    return utils.run ('VBoxManage', *map (str, args))[0]

class VM (object):
    def __init__ (self, name):
        super (VM, self).__init__ ()

        self.name = name
        self.ssh = PORT_BASE + 0 + 3 * utils.id_from_vm_name (name)
        self.nfs = PORT_BASE + 1 + 3 * utils.id_from_vm_name (name)
        self.nfs_mount = PORT_BASE + 2 + 3 * utils.id_from_vm_name (name)
        self.disk = None

        self._create ()
        _get_cloudconfig () # Make sure there is a valid cloudconfig

    def attach_disk (self, disk):
        self._detach_disk ()
        _vbox_manage_unchecked ('closemedium', disk)
        _vbox_manage (
            'storageattach', self.name,
            '--storagectl', 'SCSI',
            '--port', 2,
            '--type', 'hdd',
            '--medium', disk,
        )
        self.disk = disk

    def poweron (self):
        sys.stdout.write ('Booting VM..')
        sys.stdout.flush ()
        _vbox_manage_unchecked ('controlvm', self.name, 'poweroff')
        _vbox_manage ('startvm', self.name)

        sys.stdout.write ('.')
        sys.stdout.flush ()
        while not self.is_powered_on ():
            sys.stdout.write ('.')
            sys.stdout.flush ()
            time.sleep (1)
        print ' Done'

    def poweroff (self):
        utils.ssh_checked (self, 'sync')
        _vbox_manage_unchecked ('controlvm', self.name, 'poweroff')
        time.sleep (1) # Poweroff takes some time and may hold lock
        self._detach_disk ()

    def is_powered_on (self):
        return 0 == utils.ssh (self, 'echo', 1)[0]

    def _create (self):
        if 0 == _vbox_manage_unchecked ('showvminfo', self.name):
            return

        _vbox_manage (
            'createvm',
            '--name', self.name,
            '--ostype', 'Linux26_64',
            '--basefolder', config.user_path ('vm'),
            '--register',
        )
        _vbox_manage (
            'storagectl', self.name,
            '--name', 'SCSI',
            '--add', 'scsi',
        )
        _vbox_manage (
            'storageattach', self.name,
            '--storagectl', 'SCSI',
            '--port', 0,
            '--type', 'hdd',
            '--medium', self._get_coreos (),
        )
        _vbox_manage (
            'storageattach', self.name,
            '--storagectl', 'SCSI',
            '--port', 1,
            '--type', 'dvddrive',
            '--medium', _get_cloudconfig (),
        )
        _vbox_manage (
            'modifyvm', self.name,
            '--memory', 512,
            '--nic1', 'nat',
            '--natpf1', 'ssh,tcp,127.0.0.1,{},,22'.format (self.ssh),
            '--natpf1', 'nfs,tcp,127.0.0.1,{},,2049'.format (self.nfs),
            '--natpf1', 'nfsmount,tcp,127.0.0.1,{},,11111'.format (self.nfs_mount),
        )

    def _get_coreos (self):
        target = config.user_path ('vm/{}/coreos.vmdk'.format (self.name))
        if os.path.exists (target):
            return target

        utils.ensure_dir_for_file (target)
        shutil.copy (_get_coreos_disk (), target)

        return target

    def _detach_disk (self):
        _vbox_manage_unchecked (
            'storageattach', self.name,
            '--storagectl', 'SCSI',
            '--port', 2,
            '--type', 'hdd',
            '--medium', None,
        )
        if self.disk is not None:
            time.sleep (0.5) # Detach takes some time and may hold lock
            _vbox_manage_unchecked ('closemedium', self.disk)
            self.disk = None

    def __repr__ (self):
        return '<VM name={} ssh={}>'.format (self.name, self.ssh)
