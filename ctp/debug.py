import vm
import config

import subprocess

def debug (path):
    disk = path + '/crypt.vdi'
    m = vm.aquire_vm (disk)
    try:
        subprocess.call ([
            'ssh', 'core@localhost',
            '-p', str (m.ssh),
            '-i', config.get_ssh_private_key_file (),
            '-o', 'StrictHostKeychecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
        ])
    finally:
        vm.release_vm (m)
