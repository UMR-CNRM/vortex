"""
This package handles some common targets used at ECMWF.
"""


import footprints

from vortex.tools.targets import Target

#: No automatic export
__all__ = []


class ECMWFSequana1(Target):
    """Atos Sequana Computer."""

    _abstract = True
    _footprint = dict(
        info = 'Atos Sequana Supercomputers at ECMWF',
        attr = dict(
            sysname = dict(
                values = ['Linux', ]
            ),
            inifile = dict(
                # Always remap to the aa configuration
                default = '@target-aa.ini',
            )
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )


class EcmwfAA(ECMWFSequana1):
    """AA Computer at ECMWF."""

    _footprint = dict(
        info = 'Atos Sequana AA Supercomputer at ECMWF',
        attr = dict(
            inetname = dict(
                default = 'aa',
                values  = ['aa']
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'aa\d+-\d+')
        ),
    )


class EcmwfAB(ECMWFSequana1):
    """AB Computer at ECMWF."""

    _footprint = dict(
        info = 'Atos Sequana AB Supercomputer at ECMWF',
        attr = dict(
            inetname = dict(
                default = 'ab',
                values  = ['ab']
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'ab\d+-\d+')
        ),
    )


class EcmwfAC(ECMWFSequana1):
    """AC Computer at ECMWF."""

    _footprint = dict(
        info = 'Atos Sequana AC Supercomputer at ECMWF',
        attr = dict(
            inetname = dict(
                default = 'ac',
                values  = ['ac']
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'ac\d+-\d+')
        ),
    )


class EcmwfAD(ECMWFSequana1):
    """AD Computer at ECMWF."""

    _footprint = dict(
        info = 'Atos Sequana AA Supercomputer at ECMWF',
        attr = dict(
            inetname = dict(
                default = 'ad',
                values  = ['ad']
            ),
        ),
        only = dict(
            hostname = footprints.FPRegex(r'ad\d+-\d+')
        ),
    )
