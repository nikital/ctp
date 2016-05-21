import utils
import vm

def create (path, size, password):
    disk = path + '/crypt.vdi'
    utils.ensure_dir_for_file (disk)
    vm.create_medium (disk, size)

    password = password.encode ('base64').strip ()

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
