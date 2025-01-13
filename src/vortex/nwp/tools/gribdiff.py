"""
TODO: Module documentation.
"""

import footprints

from vortex.tools.grib import GRIBAPI_Tool

#: No automatic export
__all__ = []


class _GRIBDIFF_Plus_St:
    """Status of the GRIB comparison."""

    def __init__(self, rc, result):
        self.rc = rc
        self._result = result

    def __str__(self):
        return "{:s} | rc={:d}>".format(repr(self).rstrip(">"), self.rc)

    @property
    def result(self):
        """Indicates whether the diff succeeded or not."""
        return self._result

    def __bool__(self):
        return self.rc


class _GRIBDIFF_Plus_Res:
    """Detailed result of the GRIB comparison."""

    def __init__(self, gapi, epydiff, epydiff_res):
        self._gapi = gapi
        self._epydiff = epydiff
        self._epydiff_res = epydiff_res

    def __str__(self):
        return "{0:s} | gribapi_rc={1:d} epydiff_done={2:d}>".format(
            repr(self).rstrip(">"), self._gapi, self._epydiff
        )

    def differences(self):
        """Print detailed informations about the diff."""
        print(self._epydiff_res)


class GRIBDIFF_Plus(GRIBAPI_Tool):
    """
    Interface to gribapi commands + epygram diff (designed as a shell Addon).
    """

    _footprint = dict(
        info="Default GRIBAPI system interface",
        attr=dict(
            maxepydiff=dict(
                info="Epygram diffs are costfull, they will run only maxepydiff times",
                type=int,
                default=2,
                optional=True,
            ),
        ),
        priority=dict(
            level=footprints.priorities.top.TOOLBOX  # @UndefinedVariable
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._epycount = 0
        self._epyavail = None

    def _actual_diff(self, grib1, grib2, skipkeys, **kw):
        rc = super()._actual_diff(grib1, grib2, skipkeys, **kw)
        if not rc:
            if self._epyavail is None:
                from ..util.usepygram import epygram_checker

                self._epyavail = epygram_checker.is_available(version="1.0.0")
            if self._epyavail:
                if self._epycount < self.maxepydiff:
                    from ..util.diffpygram import EpyGribDiff

                    gdiff = EpyGribDiff(grib2, grib1)  # Ref file is first...
                    self._epycount += 1
                    res = _GRIBDIFF_Plus_Res(rc, True, str(gdiff))
                    # Save the detailed diff
                    with open(grib1 + "_epygram_diffstats.log", "w") as outfh:
                        outfh.write(gdiff.format_diff(detailed=True))
                else:
                    res = _GRIBDIFF_Plus_Res(
                        rc,
                        False,
                        "grib_compare failed (but the Epygram diffs max number is exceeded...)",
                    )
            else:
                res = _GRIBDIFF_Plus_Res(
                    rc, False, "grib_compare failed (Epygram unavailable)"
                )
        else:
            res = _GRIBDIFF_Plus_Res(rc, False, "")
        return _GRIBDIFF_Plus_St(rc, res)
