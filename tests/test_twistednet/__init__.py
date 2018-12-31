# -*- coding: utf-8 -*-

'''
FTP + e-mail based on interactions with twisted servers.
'''

from __future__ import print_function, division, absolute_import, unicode_literals


def has_ftpservers():
    try:
        import twisted.protocols.ftp
    except ImportError:
        return False
    else:
        return True
