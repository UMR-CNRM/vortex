"""
Various tools related to the IFS code.
"""

import re

from bronx.fancies import loggers
from bronx.stdtypes.date import Time

import footprints

from vortex.syntax.stdattrs import model
from ..syntax.stdattrs import arpifs_cycle

logger = loggers.getLogger(__name__)


class _IfsOutputsTimesListDesc:
    """Convert the input data to Time objects."""

    def __init__(self, attr, doc):
        self._attr = attr
        self.__doc__ = doc

    def __get__(self, instance, owner):
        return instance._tlists_store.get(self._attr, None)

    def __set__(self, instance, value):
        if value is None:
            instance._tlists_store.pop(self._attr, None)
        else:
            if not isinstance(value, list):
                raise ValueError("**value** should be a list.")
            instance._tlists_store[self._attr] = [Time(t) for t in value]

    def __delete__(self, instance):
        instance._tlists_store.pop(self._attr, None)


class IfsOutputsAbstractConfigurator(footprints.FootprintBase):
    """Abstract utility class to configure the IFS model regarding output data."""

    _abstract = True
    _collector = ("ifsoutputs_configurator",)
    _footprint = [
        model,
        arpifs_cycle,
        dict(
            attr=dict(
                fcterm_unit=dict(
                    info="The unit used in the *fcterm* attribute.",
                    values=["h", "t"],
                ),
            )
        ),
    ]

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._tlists_store = dict()

    modelstate = _IfsOutputsTimesListDesc(
        "modelstate", "The list of terms for modelstate outputs."
    )

    surf_modelstate = _IfsOutputsTimesListDesc(
        "surf_modelstate",
        "The list of terms for surface scheme modelstate outputs.",
    )

    spectral_diag = _IfsOutputsTimesListDesc(
        "spectral_diag",
        "The list of terms for spectral space diagnostics outputs.",
    )

    post_processing = _IfsOutputsTimesListDesc(
        "post_processing",
        "The list of terms for inline post-processing outputs.",
    )

    def _setup_nam_obj(self, namelist_object, namelist_name):
        """Actualy tweak the IFS namelist."""
        raise NotImplementedError()

    def __call__(self, namelist_object, namelist_name):
        """Tweak **namelist_object** that was read from the **namelist_name** file."""
        if self._tlists_store:
            self._setup_nam_obj(namelist_object, namelist_name)
            return True
        else:
            return False


class IfsOutputsConfigurator(IfsOutputsAbstractConfigurator):
    """Utility class to configure the IFS model regarding output data."""

    @staticmethod
    def _get_namblock(namelist_object, nam_block):
        """Get or create a **nam_block** namelist."""
        if nam_block in namelist_object:
            return namelist_object[nam_block]
        else:
            return namelist_object.newblock(nam_block)

    @staticmethod
    def _set_namvar_value(namblock, var, value, namname):
        """Set a value in a **namblock** namelist and log it."""
        namblock[var] = value
        logger.info(
            "Setup &%s %s=%s / (file: %s)",
            namblock.name,
            var,
            namblock.nice(value),
            namname,
        )

    @staticmethod
    def _clean_namvar(namblock, var, namname):
        """Clean the **var** value from the **namblock** namelist."""
        todo = {k for k in namblock.keys() if re.match(var + r"($|\(|%)", k)}
        if todo:
            for k in todo:
                namblock.delvar(k)
            logger.info(
                "Cleaning %s variable in namelist &%s (file: %s)",
                var,
                namblock.name,
                namname,
            )

    def _generic_terms_setup(self, namct0, namct1, what, terms, namname):
        """Setup a given kind of output data (in a generic way)."""
        if terms is not None:
            sign = -1 if self.fcterm_unit == "h" else 1
            with_minutes = any([t.minute > 0 for t in terms])
            self._clean_namvar(namct0, "NFR{:s}".format(what), namname)
            self._clean_namvar(namct0, "N{:s}TS".format(what), namname)
            self._clean_namvar(namct0, "N{:s}TSMIN".format(what), namname)
            self._set_namvar_value(
                namct1, "N1{:s}".format(what), 1 if terms else 0, namname
            )
            if terms:
                self._set_namvar_value(
                    namct0,
                    "N{:s}TS(0)".format(what),
                    sign * len(terms),
                    namname,
                )
                if with_minutes:
                    if (
                        "cy46" <= self.cycle < "cy47"
                    ):  # Temporary fix for cy46 only
                        self._set_namvar_value(
                            namct0,
                            "N{:s}TSMIN(0)".format(what),
                            len(terms),
                            namname,
                        )
                logger.info(
                    "Setting up N%sTS and N%sTSMIN in &%s (file: %s)",
                    what,
                    what,
                    namct0.name,
                    namname,
                )
                for i, t in enumerate(terms):
                    namct0["N{:s}TS({:d})".format(what, i + 1)] = sign * t.hour
                if with_minutes:
                    for i, t in enumerate(terms):
                        namct0["N{:s}TSMIN({:d})".format(what, i + 1)] = (
                            t.minute
                        )

    def _setup_nam_obj(self, namelist_object, namelist_name):
        """Actualy tweak the IFS namelist."""
        namoph = self._get_namblock(namelist_object, "NAMOPH")
        namct0 = self._get_namblock(namelist_object, "NAMCT0")
        namct1 = self._get_namblock(namelist_object, "NAMCT1")
        # First take into account the **fcterm_unit**
        self._set_namvar_value(
            namoph, "LINC", self.fcterm_unit == "h", namelist_name
        )
        # Setup outputs
        self._generic_terms_setup(
            namct0, namct1, "HIS", self.modelstate, namelist_name
        )
        self._generic_terms_setup(
            namct0, namct1, "SFXHIS", self.surf_modelstate, namelist_name
        )
        self._generic_terms_setup(
            namct0, namct1, "SDI", self.spectral_diag, namelist_name
        )
        self._generic_terms_setup(
            namct0, namct1, "POS", self.post_processing, namelist_name
        )
        # Extra fixup for fullpos
        if self.post_processing is not None:
            if not self.post_processing:
                self._set_namvar_value(namct0, "NFPOS", 0, namelist_name)
            else:
                # Do not overwrite a pre-existing positive value:
                if "NFPOS" not in namct0 or namct0["NFPOS"] == 0:
                    self._set_namvar_value(namct0, "NFPOS", 1, namelist_name)
