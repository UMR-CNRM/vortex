"""
Various System needed for NWP applications.
"""

from vortex.tools.addons import AddonGroup

# Import the proper Addon modules for footprints
from vortex.tools import folder as folder
from vortex.tools import lfi as lfi
from vortex.tools import grib as grib
from vortex.tools import listings as listings
from vortex.tools import surfex as surfex

#: No automatic export
__all__ = []


class NWPAddonsGroup(AddonGroup):
    """A set of usual NWP Addons."""

    _footprint = dict(
        info="Default NWP Addons",
        attr=dict(
            kind=dict(
                values=[
                    "nwp",
                ],
            ),
        ),
    )

    _addonslist = (
        "allfolders",  # Folder like...
        "lfi",
        "iopoll",  # Wonderful FA/LFI world...
        "grib",
        "gribapi",  # GRIB stuff...
        "arpifs_listings",  # Obscure IFS/Arpege listings...
        "sfx",  # Surfex...
    )
