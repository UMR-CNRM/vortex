# -*- coding: utf-8 -*-

'''
Utility methods
'''

import platform


def _get_port_number(default):
    if platform.system() == 'Linux':
        from vortex.tools.net import LinuxNetstats
        return LinuxNetstats().available_localport()
    else:
        return default


def get_ftp_port_number():
    return _get_port_number(21210)


def get_email_port_number():
    return _get_port_number(25250)
