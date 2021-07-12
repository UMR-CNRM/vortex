# -*- coding: utf-8 -*-

"""
This module contains the services specifically needed by Olive.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import pprint

from vortex.tools.actions import actiond as ad
from vortex.tools.services import AbstractRdTemplatedMailService

from . import swapp

#: Export nothing
__all__ = []


class OliveMailService(AbstractRdTemplatedMailService):
    """Class responsible for sending predefined mails.

    This class should not be called directly.
    """

    _footprint = dict(
        info = 'Olive predefined mail services class',
        attr = dict(
            kind = dict(
                values   = ['olivemail'],
            ),
        )
    )

    _TEMPLATES_SUBDIR = 'olivemails'

    def substitution_dictionary(self, add_ons=None):
        sdict = super(OliveMailService, self).substitution_dictionary(add_ons=add_ons)
        if 'flow' in ad.actions and any(ad.flow_status()):
            flowconf = ad.flow_conf(dict())[0]
            flowout = 'unknown'
            for k, v in flowconf.items():
                if k.endswith('JOBOUT'):
                    flowout = v.split('/')[-1]
                    break
            sdict['flowinfo'] = pprint.pformat(flowconf, indent=2)
            sdict['taskid'] = flowout
        else:
            sdict['flowinfo'] = 'No active flow scheduler'
            sdict['taskid'] = 'unknown'
        sdict['label'] = swapp.olive_label(self.sh, self.sh.env,
                                           self.sh.default_target.generic())
        return sdict
