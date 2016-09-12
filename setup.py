#!/usr/bin/env python3

from setuptools import setup

setup (name='ctp',
       version='0.1',
       author='Nikita Leshenko', author_email='nikita@lesheno.net',
       url='https://github.com/nikital/ctp',
       packages=['ctp'],
       entry_points={
           'console_scripts': [
               'ctp-mount = ctp.__main__:mount_command',
               'ctp-umount = ctp.__main__:umount_command',
               'ctp-create = ctp.__main__:create_command',
               'ctp-debug = ctp.__main__:debug_command',
           ]
       })
