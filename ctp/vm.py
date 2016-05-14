import config
import utils

import os
import shutil
import sys
import tempfile
import urllib

DISK_URL = 'https://stable.release.core-os.net/amd64-usr/current/coreos_production_virtualbox_image.vmdk.bz2'
PORT_BASE = 11100

def _print_progress (blocks, block_size, total_size):
    percent = 1.0 * blocks * block_size / total_size
    sys.stdout.write ('\r{:3.0f}% [{:50}] '.format (percent * 100, int (50 * percent) * '='))
    sys.stdout.flush ()

def _get_compressed_disk ():
    target = config.user_path ('vm/disk/coreos.vmdk.bz2')
    if os.path.exists (target):
        return target

    print 'Downloading CoreOS disk'
    utils.ensure_dir_for_file (target)
    sys.stdout.write ('Initializing connection...')
    sys.stdout.flush ()
    filename, headers = urllib.urlretrieve (DISK_URL, reporthook=_print_progress)
    print 'Done.'
    shutil.move (filename, target)

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
        self.ssh_port = PORT_BASE + 0 + 3 * utils.id_from_vm_name (name)
        self.nfs_port = PORT_BASE + 1 + 3 * utils.id_from_vm_name (name)
        self.nfs_mount_port = PORT_BASE + 2 + 3 * utils.id_from_vm_name (name)

        self._create ()
        _get_cloudconfig () # Make sure there is a valid cloudconfig

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
            '--medium', self._get_disk (),
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
            '--natpf1', 'ssh,tcp,127.0.0.1,{},,22'.format (self.ssh_port),
            '--natpf1', 'nfs,tcp,127.0.0.1,{},,2049'.format (self.nfs_port),
            '--natpf1', 'nfsmount,tcp,127.0.0.1,{},,11111'.format (self.nfs_mount_port),
        )

    def _get_disk (self):
        target = config.user_path ('vm/{}/coreos.vmdk'.format (self.name))
        if os.path.exists (target):
            return target

        target_bz2 = target + '.bz2'
        utils.ensure_dir_for_file (target_bz2)
        shutil.copy (_get_compressed_disk (), target_bz2)
        print 'Decompressing CoreOS disk'
        utils.run_checked ('bunzip2', target_bz2)

        return target
