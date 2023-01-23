"""
TODO: Module documentation
"""

from vortex.data.flow import PeriodFlowResource

#: No automatic export
__all__ = []


class PlayfullPeriodFlow(PeriodFlowResource):
    """Just a small demo of a period based flow resource."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['playfullperiod']
            ),
            nativefmt = dict(
                default = 'txt'
            )
        )
    )

    @property
    def realkind(self):
        return 'playfullperiod'
