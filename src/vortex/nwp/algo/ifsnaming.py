"""
Ensemble of classes that deal with input/output filenames for IFS/Arpege related
binaries (those that inherits from :class:`IFSParallel`).

Since input/output names may vary depending on the code's cycle, the configuration
number, or basically anything that might emerge from the mind of a twisted
developer... :mod:`footprints` is used to find out the most appropriate name
depending on various things:

    * The model name (e.g. Arpege, Arome, Surfex)
    * The file format (e.g. FA, GRIB)
    * The binary cycle number (e.g. cy42_op2)
    * The configuration number (e.g. 1, 701)
    * The experiment name (e.g; FCST, CANS)

An additional attribute *kind* is mandatory, it helps to describe which type of
input/output file is targeted. The developer can also add customised attributes as
she/he may see fit.

The base class for any object dealing with IFS/Arpege file names is
:class:`IFSNamingConvention`. The "ifsnamingconv" footprints' collector is used.

Do not create :class:`IFSNamingConvention` objects directly. Instead, use the
:meth:`IFSParallel.naming_convention` method.
"""

import math

import footprints

from vortex.syntax.stdattrs import model, actualfmt
from ..syntax.stdattrs import arpifs_cycle

#: No automatic export
__all__ = []


# Base & Generic classes
# ##############################################################################


class IFSNamingConvention(footprints.FootprintBase):
    """Abstract class for any object representing an IFS/Arpege naming scheme."""

    _abstract = True
    _collector = ("ifsnamingconv",)
    _footprint = [
        model,
        actualfmt,
        arpifs_cycle,
        dict(
            attr=dict(
                kind=dict(info="The type of targeted input/output file"),
                conf=dict(
                    info="IFS/Arpege configuration number",
                    type=int,
                ),
                xpname=dict(
                    info="IFS/Arpege experiment name",
                ),
                actualfmt=dict(
                    info="The target file format",
                    optional=True,
                ),
            )
        ),
    ]

    def _naming_format_string(self, **kwargs):
        """Return the format string that will be used to generate the filename."""
        raise NotImplementedError()

    def __call__(self, **kwargs):
        return self._naming_format_string(**kwargs).format(
            xpname=self.xpname,
            conf=self.conf,
            fmt=self.actualfmt,
            model=self.model,
            **kwargs,
        )


# Activate the footprint's fasttrack on the ifsnamingconv collector
ncollect = footprints.collectors.get(tag="ifsnamingconv")
ncollect.fasttrack = ("kind",)
del ncollect


class IFSHardWiredNamingConvention(IFSNamingConvention):
    """
    A very basic object where the user can provide the format string on its own
    using the *namingformat*. For debugging only...
    """

    _footprint = dict(
        attr=dict(namingformat=dict()),
        priority=dict(
            level=footprints.priorities.top.TOOLBOX  # @UndefinedVariable
        ),
    )

    def _naming_format_string(self, **kwargs):
        return self.namingformat


# Climatology files names
# ##############################################################################


class ModelClimName(IFSNamingConvention):
    """An IFS/Arpege model clim."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "modelclim",
                ],
            ),
            conf=dict(
                outcast=[
                    701,
                ],
            ),
            model=dict(
                outcast=[
                    "surfex",
                ]
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "Const.Clim"


class SurfexClimName(IFSNamingConvention):
    """A Surfex model clim."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "modelclim",
                ],
            ),
            model=dict(
                values=[
                    "surfex",
                ]
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "Const.Clim.sfx"


class TargetClimName(IFSNamingConvention):
    """A BDAP clim file or a target domain IFS/Arpege clim file."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "targetclim",
                ],
            ),
            model=dict(
                outcast=[
                    "surfex",
                ]
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "const.clim.{area:s}"


class SurfexTargetClimName(IFSNamingConvention):
    """A target domain Surfex clim file."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "targetclim",
                ],
            ),
            model=dict(
                values=[
                    "surfex",
                ]
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "const.clim.sfx.{area:s}"


class CanariModelClimName(IFSNamingConvention):
    """An IFS/Arpege model clim (specific naming for Canari)."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "modelclim",
                ],
            ),
            conf=dict(
                values=[
                    701,
                ],
            ),
            model=dict(
                outcast=[
                    "surfex",
                ]
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "ICMSH{xpname:s}CLIM"


class CanariClosestModelClimName(CanariModelClimName):
    """An IFS/Arpege model clim for the closest month (specific naming for Canari)."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "closest_modelclim",
                ],
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "ICMSH{xpname:s}CLI2"


# Initial conditions file names
# ##############################################################################


class InitialContionsName(IFSNamingConvention):
    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "ic",
                ],
            ),
            model=dict(
                outcast=[
                    "surfex",
                ]
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "ICMSH{xpname:s}INIT"


class SurfexInitialContionsName(IFSNamingConvention):
    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "ic",
                ],
            ),
            model=dict(
                values=[
                    "surfex",
                ]
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "ICMSH{xpname:s}INIT.sfx"


class IauAnalysisName(IFSNamingConvention):
    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "iau_analysis",
                ],
            ),
            model=dict(
                outcast=[
                    "surfex",
                ]
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "ICIAU{xpname:s}IN{number:02d}"


class IauBackgroundName(IFSNamingConvention):
    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "iau_background",
                ],
            ),
            model=dict(
                outcast=[
                    "surfex",
                ]
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "ICIAU{xpname:s}BK{number:02d}"


# Lateral Boundary Conditions Files
# ##############################################################################


class LAMBoundaryConditionsName(IFSNamingConvention):
    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "lbc",
                ],
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "ELSCF{xpname:s}ALBC{number:03d}"


# Strange files used in the EDA
# ##############################################################################


class IfsEdaInputName(IFSNamingConvention):
    _abstract = True
    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "edainput",
                ],
            ),
            variant=dict(
                values=[
                    "infl",
                    "infl_factor",
                    "mean",
                    "covb",
                ],
            ),
            totalnumber=dict(
                info="The total number of input files",
                type=int,
                optional=True,
            ),
        )
    )

    @property
    def _number_fmt(self):
        if self.totalnumber:
            ndigits = max(int(math.floor(math.log10(self.totalnumber))) + 1, 3)
        else:
            ndigits = 3
        return "{number:0" + str(ndigits) + "d}"


class IfsEdaArpegeFaInputName(IfsEdaInputName):
    _footprint = dict(
        attr=dict(
            model=dict(
                values=[
                    "arpege",
                ]
            ),
            actualfmt=dict(
                values=[
                    "fa",
                ]
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "FAMEMBER_" + self._number_fmt


class IfsEdaArpegeGribInputName(IfsEdaInputName):
    _footprint = dict(
        attr=dict(
            model=dict(
                values=[
                    "arpege",
                ]
            ),
            actualfmt=dict(
                values=[
                    "grib",
                ]
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "GRIBERm" + self._number_fmt


class IfsEdaAromeInputName(IfsEdaInputName):
    _footprint = dict(
        attr=dict(
            model=dict(
                values=[
                    "arome",
                ]
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "ELSCF{xpname:s}ALBC" + self._number_fmt


class IfsEdaOutputName(IFSNamingConvention):
    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "edaoutput",
                ],
            ),
            variant=dict(
                values=[
                    "infl",
                    "infl_factor",
                    "mean",
                    "covb",
                ],
            ),
        )
    )

    def _naming_format_string(self, **kwargs):
        return "ICMSH{xpname:s}+{term.fmth}_m{number:03d}"
