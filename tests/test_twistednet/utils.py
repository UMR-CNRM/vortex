"""
Utility methods
"""

import platform
import time


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


def wait_for_port(port):
    if platform.system() == 'Linux':
        from vortex.tools.net import LinuxNetstats
        lns = LinuxNetstats()
        while not lns.check_localport(port):
            time.sleep(0.1)
        time.sleep(0.1)
    else:
        # Well... this is a bti crude !
        time.sleep(3)
