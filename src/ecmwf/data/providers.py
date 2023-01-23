"""
This package is used to implement the Archive Store class only used at ECMWF.
"""

import footprints
from vortex.data.providers import Remote


class RemoteECMWF(Remote):
    """Specific Remote class at ECMWF (allows ectrans and ecfs tubes)"""
    _footprint = dict(
        info = "Specific remote provider at ECMWF",
        attr = dict(
            tube=dict(
                info="The protocol used to access the data.",
                values=["ectrans", "ecfs"],
                outcast = ['scp', 'ftp', 'rcp', 'file', 'symlink']
            )
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )
