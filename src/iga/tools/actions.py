#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from vortex.toolbox import sessions
from vortex.tools.actions import Action, actiond

import footprints
logger = footprints.loggers.getLogger(__name__)


class SendAlarm(Action):
    """
    Class responsible for sending alarm
    """

    def __init__(self, kind='alarm', service=None, active=True):
        super(SendAlarm, self).__init__(kind)

    def service_info(self, **kw):
        """Avoid forcing the user to tell it's hostname"""
        sh = sessions.system()
        kw.setdefault('hostname', sh.hostname)
        return super(SendAlarm, self).service_info(**kw)


class SendAgt(Action):
    """
    Class responsible for sending data to the Transfer Agent (BDAP, BDPE, BDM).
    """

    def __init__(self, kind='agt', service='routing', active=True):
        super(SendAgt, self).__init__(kind)


actiond.add(SendAlarm(), SendAgt())
