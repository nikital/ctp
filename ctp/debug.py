from . import vm
from . import config

import subprocess

def debug (path):
    config.verify_no_mount (path)
    disk = path + '/crypt.vdi'
    with config.mount_context (path):
        with vm.vm_context (disk) as m:
            subprocess.call ([
                'ssh', 'core@localhost',
                '-p', str (m.ssh),
                '-i', config.get_ssh_private_key_file (),
                '-o', 'StrictHostKeychecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
            ])
