#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

def setresprev(e, res, prev_zero='AM'):
    """
    Defines actual HH values for previous and next run.
    Environment variables defined are::
    * RESPREV
    * RESPREV0
    * RESPREV3
    """
    if res == 0:
        if prev_zero not in ('AM', 'CM'):
            raise ValueError("Accepted values : 'AM', 'CM'")
        e.RESPREV = prev_zero
        e.RESPREV0 = prev_zero
        e.RESPREV3 = 'TR'
    elif res == 3:
        e.RESPREV = 'TR'
        e.RESPREV0 = 'AM'
        e.RESPREV3 = 'SX'
    elif res == 6:
        e.RESPREV = 'SX'
        e.RESPREV0 = 'SX'
        e.RESPREV3 = 'NF'
    elif res == 9:
        e.RESPREV = 'NF'
        e.RESPREV0 = 'SX'
        e.RESPREV3 = 'PM'
    elif res == 12:
        e.RESPREV = 'PM'
        e.RESPREV0 = 'PM'
        e.RESPREV3 = 'QZ'
    elif res == 15:
        e.RESPREV = 'QZ'
        e.RESPREV0 = 'PM'
        e.RESPREV3 = 'DH'
    elif res == 18:
        e.RESPREV = 'DH'
        e.RESPREV0 = 'DH'
        e.RESPREV3 = 'VU'
    elif res == 21:
        e.RESPREV = 'VU'
        e.RESPREV0 = 'DH'
        e.RESPREV3 = 'CM'
    else:
        raise ValueError("RESEAU unknown")
