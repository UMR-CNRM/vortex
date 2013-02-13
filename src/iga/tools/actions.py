#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import logging

from vortex.tools.actions import Action, actiond


class SendAlarm(Action):
    r"""
    Class responsible for sending alarm. You never call this class
    directly. You must use x :func:`logger`.
    """

    def __init__(self, kind='alarm'):
        super(SendAlarm, self).__init__(kind)


class SendAgt(Action):
    r"""
    Class responsible for sending data towards the BDAP machine. You never call this class
    directly. You must use x :func:`sendbdap`.

    Arguments:
        kw (dict): mandatory arguments used to send the data
    """

    def __init__(self, kind='agt', service='routing'):
        super(SendAgt, self).__init__(kind)


actiond.add(SendAlarm(), SendAgt())
