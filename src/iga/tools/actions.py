#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from vortex.tools.actions import Action, actiond


class SendAlarm(Action):
    """
    Class responsible for sending alarm
    """

    def __init__(self, kind='alarm', service=None, active=True):
        super(SendAlarm, self).__init__(kind)


class SendAgt(Action):
    """
    Class responsible for sending data towards the BDAP machine.

    Arguments:
     * kw (dict): mandatory arguments used to send the data
    """

    def __init__(self, kind='agt', service='routing', active=True):
        super(SendAgt, self).__init__(kind)


actiond.add(SendAlarm(), SendAgt())
