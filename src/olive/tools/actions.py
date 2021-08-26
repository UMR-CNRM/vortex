# -*- coding: utf-8 -*-

"""
Actions specific to Olive needs.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.tools.actions import TemplatedMail, actiond

#: Export nothing
__all__ = []


class OliveMail(TemplatedMail):
    """
    Class responsible for sending pre-defined mails for Olive.
    """

    def __init__(self, kind='olivemail', service='olivemail', active=True,
                 catalog=None, inputs_charset=None):
        super(OliveMail, self).__init__(kind=kind, active=active, service=service,
                                        catalog=catalog, inputs_charset=inputs_charset)
        self.off()  # Inactive by default


actiond.add(OliveMail(inputs_charset='utf-8'))
