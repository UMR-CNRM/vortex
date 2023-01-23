"""
This module contains AlgoComponents that just generate a simple JSON
file (or fail).
"""

from vortex.algo.components import AlgoComponent, AlgoComponentError
from vortex.syntax.stdattrs import date, cutoff, member

#: No automatic export
__all__ = []


class BeaconJsonFileDumper(AlgoComponent):
    """Dump a simple JSON file and possibly fail on request"""

    _footprint = [
        date,
        cutoff,
        member,
        dict(
            attr = dict(
                kind = dict(
                    values  = ['play_beacon'],
                ),
                identifier = dict(
                ),
                failer = dict(
                    type = bool,
                    optional = True,
                    default = False
                )
            )
        )
    ]

    def execute(self, rh, opts):
        """Create a useledd JSON file"""
        self.system.json_dump(dict(tag=self.identifier,
                                   date=str(self.date),
                                   cutoff=self.cutoff,
                                   member=self.member),
                              'the_file.json')
        self.system.sleep(0.2)
        if self.failer:
            raise AlgoComponentError("This is a failer play_beacon !")
