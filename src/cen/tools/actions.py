#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Actions specific to CEN needs.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.tools.actions import Action, actiond
from vortex.util.config import GenericConfigParser

#: Export nothing
__all__ = []


class CenMail(Action):
    """
    Class responsible for sending pre-defined mails.
    """

    def __init__(self, kind='cenmail', service='cenmail', active=True,
                 catalog=None, inputs_charset=None):
        super(CenMail, self).__init__(kind=kind, active=active, service=service)
        self.off()  # Inactive by default
        self.catalog = catalog or GenericConfigParser('@cenmail-inventory.ini',
                                                      encoding=inputs_charset)
        self.inputs_charset = inputs_charset

    def service_info(self, **kw):
        """Kindly propose the permanent directory and catalog to the final service"""
        kw.setdefault('catalog', self.catalog)
        kw.setdefault('inputs_charset', self.inputs_charset)
        return super(CenMail, self).service_info(**kw)

    def execute(self, *args, **kw):
        """
        Perform the action through a service. Extraneous arguments (not included
        in the footprint) are collected and explicitely transmitted to the service
        in a dictionary.
        """
        rc = None
        service = self.get_active_service(**kw)
        if service:
            options = {k: v for k, v in kw.items() if k not in service.footprint_attributes}
            rc = service(options)
        return rc


actiond.add(CenMail(inputs_charset='utf-8'))
