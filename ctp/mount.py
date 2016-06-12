import vm
import utils
import config
from errors import CTPError

import sys

# TODO(nikita) m is a shitty name
def _open_luks (m, password, password_callback):
    open_successfull = False
    while not open_successfull:
        code, output = utils.ssh (
            m,
            'echo', password.encode ('base64').strip (),
            '|', 'base64', '-d',
            '|', 'sudo', 'cryptsetup', '-q', 'luksOpen', '/dev/sdb', 'sdb',
        )

        if code == 0:
            open_successfull = True
        elif code == 2:
            if password_callback is None:
                raise CTPError ('Bad password')
            else:
                print >>sys.stderr, 'Bad password. Please try again.'
                password = password_callback ()
        else:
            raise CTPError ('luksOpen failed with code {}'.format (code))

def mount (path, mount_point, password, password_callback=None):
    config.verify_no_mount (path)
    disk = path + '/crypt.vdi'
    utils.ensure_dir (mount_point)
    m = vm.aquire_vm (disk)

    try:
        config.set_mount (path, m.name, mount_point)
        _open_luks (m, password, password_callback)
        utils.ssh_checked (m, 'sudo', 'mount', '/dev/mapper/sdb', '/mnt')
        utils.run_checked (
            'mount_nfs',
            '-o', 'port={}'.format (m.nfs),
            '-o', 'mountport={}'.format (m.nfs_mount),
            'localhost:/mnt', mount_point
        )
    except:
        vm.release_vm (m)
        config.remove_mount (path)
        raise
    utils.run_checked ('open', mount_point)

def unmount (path):
    vm_name, mount_point = config.get_mount (path)
    m = vm.attach_vm (vm_name)

    utils.run_checked ('umount', mount_point)
    config.remove_mount (path)

    utils.ssh_checked (m, 'sudo', 'systemctl', 'stop', 'nfs-server')
    utils.ssh_checked (m, 'sudo', 'umount', '/mnt')
    utils.ssh_checked (m, 'sudo', 'cryptsetup', '-q', 'luksClose', 'sdb')
    utils.ssh_checked (m, 'sync')
    vm.release_vm (m)

def list_mounts ():
    for mount, (vm, mount_point) in config.get_all_mounts ().iteritems ():
        print '{} at {} via {}'.format (mount, mount_point, vm)
