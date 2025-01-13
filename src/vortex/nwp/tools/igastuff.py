"""
TODO: Module documentation.
"""

import re

#: No automatic export
__all__ = []

#: Specific tricks for base naming in iga fuzzy namespace.
fuzzystr = dict(
    histfix=dict(
        historic=dict(
            pearp="prev",
            arome="AROM",
            arpege="arpe",
            arp_court="arpe",
            aearp="arpe",
            aladin="ALAD",
            surfex="SURF",
        )
    ),
    prefix=dict(
        # LFM 2016/12/30: It was dble='PA' but apparently it's wrong. No idea why...
        gridpoint=dict(oper="PE", dble="PE", mirr="PE", hycom_grb="vent"),
        historic=dict(
            hycom="s_init0_", mfwam="BLS_", mfwam_BLS="BLS_", mfwam_LAW="LAW_"
        ),
        analysis=dict(hycom="s_init0_", mfwam="LAW_"),
    ),
    suffix=dict(
        bgstderr=dict(input="in", output="out"),
        analysis=dict(
            hycom_hycom=".gz", hycom_surcotes=".gz", hycom_surcotes_oi=".gz"
        ),
        historic=dict(
            surfex_arpege=".sfx",
            surfex_aearp=".sfx",
            hycom_hycom=".gz",
            hycom_surcotes=".gz",
            hycom_surcotes_oi=".gz",
        ),
        gridpoint=dict(hycom_grb="grb"),
    ),
    term0003=dict(
        bgstderr=dict(input="", output="_assim"),
    ),
    term0009=dict(
        bgstderr=dict(input="", output="_production"),
    ),
    term0012=dict(
        bgstderr=dict(input="_production_dsbscr", output="_production_dsbscr"),
    ),
    varbcarpege=dict(
        varbc=dict(input=".cycle_arp", output=".cycle"),
    ),
    varbcaladin=dict(
        varbc=dict(input=".cycle_alad", output=".cycle"),
    ),
    varbcarome=dict(
        varbc=dict(input=".cycle_aro", output=".cycle"),
    ),
    surf0000=dict(
        histsurf=dict(input="INIT_SURF", output="INIT_SURF"),
        historic=dict(input="INIT_SURF", output="INIT_SURF"),
    ),
    surf0003=dict(
        histsurf=dict(input="PREP", output="AROMOUT_.0003"),
        historic=dict(input="PREP", output="AROMOUT_.0003"),
    ),
    surf0006=dict(
        histsurf=dict(input="PREP", output="AROMOUT_.0006"),
        historic=dict(input="PREP", output="AROMOUT_.0006"),
    ),
)

arpcourt_vconf = ("courtfr", "frcourt", "court")


def fuzzyname(entry, realkind, key, default=None):
    """Returns any non-standard naming convention in the operational namespace."""
    try:
        return fuzzystr[entry][realkind][key]
    except KeyError:
        if default is not None:
            return default
        raise


def archive_suffix(model, cutoff, date, vconf=None):
    """Returns the suffix for iga filenames according to specified ``model``, ``cutoff`` and ``date`` hour."""

    hh = range(0, 21, 3)
    hrange = []
    for h in hh:
        hrange.append("%02d" % h)

    if cutoff == "assim":
        rr = dict(zip(zip((cutoff,) * len(hrange), hh), hrange))
    else:
        if re.search(r"court|arome", model) or vconf in arpcourt_vconf:
            rr = dict(
                zip(
                    zip((cutoff,) * len(hrange), hh),
                    ("CM", "TR", "SX", "NF", "PM", "QZ", "DH", "VU"),
                )
            )
        else:
            rr = dict(
                zip(
                    zip((cutoff,) * len(hrange), hh),
                    ("AM", "TR", "SX", "NF", "PM", "QZ", "DH", "VU"),
                )
            )

    return str(rr[(cutoff, date.hour)])


class _BaseIgakeyFactory(str):
    """
    Given the vapp/vconf, returns a default value for the igakey attribute.

    Needs to be subclassed !
    """

    _re_appconf = re.compile(r"^(\w+)/([\w@]+)$")
    _keymap = {}

    def __new__(cls, value):
        """
        If the input string is something like "vapp/vconf", use a mapping
        between vapp/vconf pairs and the igakey (see _keymap).
        If no mapping is found, it returns vapp.
        """
        val_split = cls._re_appconf.match(value)
        if val_split:
            value = cls._keymap.get(val_split.group(1), {}).get(
                val_split.group(2), val_split.group(1)
            )
        return str.__new__(cls, value)


class IgakeyFactoryArchive(_BaseIgakeyFactory):
    """
    Given the vapp/vconf, returns a default value for the igakey attribute
    """

    _keymap = {
        "arpege": {
            "4dvarfr": "arpege",
            "4dvar": "arpege",
            "pearp": "pearp",
            "aearp": "aearp",
            "courtfr": "arpege",
            "frcourt": "arpege",
            "court": "arpege",
        },
        "mocage": {
            "camsfcst": "macc",
            "camsassim": "macc",
        },
        "arome": {
            "3dvarfr": "arome",
            "france": "arome",
            "pegase": "pegase",
        },
        "aladin": {
            "antiguy": "antiguy",
            "caledonie": "caledonie",
            "nc": "caledonie",
            "polynesie": "polynesie",
            "reunion": "reunion",
        },
        "hycom": {
            "atl@anarp": "surcotes",
            "med@anarp": "surcotes",
            "atl@fcarp": "surcotes",
            "med@fcarp": "surcotes",
            "atl@anaro": "surcotes",
            "med@anaro": "surcotes",
            "atl@fcaro": "surcotes",
            "med@fcaro": "surcotes",
            "atl@fcaoc": "surcotes",
            "med@fcaoc": "surcotes",
            "oin@ancep": "surcotes_oi",
            "oin@fcaro": "surcotes_oi",
        },
        "mfwam": {
            "globalcep02": "mfwamglocep02",
            "globalcep01": "mfwamglocep01",
            "reuaro01": "mfwamreuaro",
            "polyaro01": "mfwampolyaro",
            "caledaro01": "mfwamcaledaro",
            "globalarp02": "mfwamgloarp02",
            "globalarpc02": "mfwamgloarpc02",
            "atourxarp01": "mfwamatourx01arp",
            "euratarpc01": "mfwameurcourt",
            "frangparo0025": "mfwamfrangp0025",
            "frangparoifs0025": "mfwamfrangp0025ifs",
            "assmp1": "mfwamassmp1",
            "assmp2": "mfwamassmp2",
            "assms1": "mfwamassms1",
            "assms2": "mfwamassms2",
            "angola0025": "mfwamangola",
        },
    }


class IgakeyFactoryInline(_BaseIgakeyFactory):
    """
    Given the vapp/vconf, returns a default value for the igakey attribute
    """

    _keymap = {
        "arpege": {
            "4dvarfr": "france",
            "4dvar": "france",
            "pearp": "pearp",
            "aearp": "aearp",
            "courtfr": "frcourt",
            "frcourt": "frcourt",
            "court": "frcourt",
        },
        "arome": {
            "3dvarfr": "france",
            "france": "france",
            "pegase": "pegase",
        },
        "aladin": {
            "antiguy": "antiguy",
            "caledonie": "caledonie",
            "nc": "caledonie",
            "polynesie": "polynesie",
            "reunion": "reunion",
        },
        "hycom": {
            "atl@anarp": "surcotes",
            "med@anarp": "surcotes",
            "atl@fcarp": "surcotes",
            "med@fcarp": "surcotes",
            "atl@ancep": "surcotes",
            "med@ancep": "surcotes",
            "atl@fccep": "surcotes",
            "med@fccep": "surcotes",
            "atl@anaro": "surcotes",
            "med@anaro": "surcotes",
            "atl@fcaro": "surcotes",
            "med@fcaro": "surcotes",
            "atl@red": "surcotes",
            "med@red": "surcotes",
            "oin@ancep": "surcotes_oi",
            "oin@fcaro": "surcotes_oi",
            "oin@red": "surcotes_oi",
        },
        "mfwam": {
            "globalcep02": "mfwamglocep02",
            "globalcep01": "mfwamglocep01",
            "reuaro01": "mfwamreuaro",
            "polyaro01": "mfwampolyaro",
            "caledaro01": "mfwamcaledaro",
            "globalarp02": "mfwamgloarp02",
            "globalarpc02": "mfwamgloarpc02",
            "atourxarp01": "mfwamatourx01arp",
            "euratarpc01": "mfwameurcourt",
            "frangparo0025": "mfwamfrangp0025",
            "frangparoifs0025": "mfwamfrangp0025ifs",
            "assmp1": "mfwamassmp1",
            "assmp2": "mfwamassmp2",
            "assms1": "mfwamassms1",
            "assms2": "mfwamassms2",
            "angola0025": "mfwamangola",
        },
    }
