"""
Additional info resources for DAVAI.
"""

from vortex.data.outflow import StaticResource
from vortex.data.contents import JsonDictContent


class XPinfo(StaticResource):
    """Contains info about an experiment."""
    _footprint = dict(
        info = 'Contains info about an experiment.',
        attr = dict(
            kind = dict(
                values = ['xpinfo']
            ),
            nativefmt = dict(
                values = ['json', ]
            ),
            clscontents = dict(
                default  = JsonDictContent
            ),
        )
    )

    @property
    def realkind(self):
        return 'xpinfo'


class TrolleyOfSummaries(StaticResource):
    """Trolley of Summary of task(s)."""
    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['trolley']
            ),
            nativefmt = dict(
                values = ['tar', ]
            ),
        )
    )

    @property
    def realkind(self):
        return 'trolley'
