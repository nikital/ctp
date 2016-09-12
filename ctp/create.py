from . import utils
from . import vm
from . import config

import base64

def create (path, size, password):
    with config.mount_context (path):
        disk = path + '/crypt.vdi'
        utils.ensure_dir_for_file (disk)
        vm.create_medium (disk, size)

        password = base64.b64encode (password.encode ()).decode ()

        with vm.vm_context (disk) as m:
            utils.ssh_checked (
                m,
                'echo', password,
                '|', 'base64', '-d',
                '|', 'sudo', 'cryptsetup', '-q', 'luksFormat', '/dev/sdb',
            )
            utils.ssh_checked (
                m,
                'echo', password,
                '|', 'base64', '-d',
                '|', 'sudo', 'cryptsetup', '-q', 'luksOpen', '/dev/sdb', 'sdb'
            )
            utils.ssh_checked (m, 'sudo', 'mkfs.ext4', '/dev/mapper/sdb')
            utils.ssh_checked (m, 'sudo', 'cryptsetup', 'luksClose', 'sdb')
