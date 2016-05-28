import vm
import utils
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
            '|', 'sudo', 'cryptsetup', '-q', 'luksOpen', '/dev/sdb', 'sdb'
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
    disk = path + '/crypt.vdi'
    m = vm.aquire_vm (disk)
    utils.ensure_dir (mount_point)

    try:
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
        raise
