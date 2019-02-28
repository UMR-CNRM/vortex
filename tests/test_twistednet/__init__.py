# -*- coding: utf-8 -*-

'''
FTP + e-mail based on interactions with twisted servers.
'''

from __future__ import print_function, division, absolute_import, unicode_literals


def has_ftpservers():
    try:
        from twisted.protocols.ftp import FTP, FTPFactory, FTPRealm, AUTH_FAILURE
        from twisted.cred.portal import Portal
        from twisted.cred.checkers import InMemoryUsernamePasswordDatabaseDontUse
        from twisted.internet import reactor
    except ImportError:
        return False
    else:
        return True


def has_mailservers():
    try:
        from zope.interface import implementer
        from twisted.internet import defer, reactor
        from twisted.mail import smtp
        from twisted.cred.checkers import AllowAnonymousAccess
        from twisted.cred.portal import IRealm
        from twisted.cred.portal import Portal
    except ImportError:
        return False
    else:
        return True
