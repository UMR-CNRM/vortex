#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module contains the services specifically needed by Olive.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import pprint

from bronx.stdtypes import date
import footprints
from vortex.tools.actions import actiond as ad
from vortex.tools.services import TemplatedMailService

from . import swapp

#: Export nothing
__all__ = []


class OliveMailService(TemplatedMailService):
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
        fpdefaults = footprints.setup.defaults
        sdict['fpdefaults'] = pprint.pformat(fpdefaults, indent=2)
        sdict['timeid'] = fpdefaults.get('date', None)
        if sdict['timeid']:
            sdict['timeid'] = sdict['timeid'].vortex(cutoff=fpdefaults.get('cutoff', 'X'))
        return sdict

    def _template_name_rewrite(self, tplguess):
        if not tplguess.startswith('@olivemails/'):
            tplguess = '@olivemails/' + tplguess
        if not tplguess.endswith('.tpl'):
            tplguess += '.tpl'
        return tplguess

    def header(self):
        """String prepended to the message body."""
        now = date.now()
        stamp1 = now.strftime('%A %d %B %Y')
        stamp2 = now.strftime('%X')
        return 'Email sent on {} at {} (from: {}).\n--\n\n'.format(stamp1, stamp2,
                                                                   self.sh.default_target.hostname)
