"""
TODO: module documentation.
"""

from vortex.tools.addons import AddonGroup

# Load the proper Addon modules...
from . import polling  # @UnusedImport

#: No automatic export
__all__ = []


class MocageAddonsGroup(AddonGroup):
    """A set of usual Mocage Addons."""

    _footprint = dict(
        info = 'Default Mocage Addons',
        attr = dict(
            kind = dict(
                values = ['mocage'],
            ),
        )
    )

    _addonslist = ('iopoll_mocage', 'iopoll_mocacc')  # IO polling
