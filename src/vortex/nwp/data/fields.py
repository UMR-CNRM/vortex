"""
TODO: Module documentation.
"""

from vortex.data.outflow import StaticResource
from vortex.data.flow import GeoFlowResource
from vortex.syntax.stdattrs import date_deco, cutoff_deco
from vortex.syntax.stddeco import namebuilding_delete, namebuilding_insert

#: No automatic export
__all__ = []


@namebuilding_insert("radical", lambda s: s.fields)
@namebuilding_insert(
    "src",
    lambda s: [
        s.origin,
    ],
)
@namebuilding_delete("fmt")
class RawFields(StaticResource):
    _footprint = [
        date_deco,
        cutoff_deco,
        dict(
            info="File containing a limited list of observations fields",
            attr=dict(
                kind=dict(values=["rawfields"]),
                origin=dict(
                    values=[
                        "bdm",
                        "nesdis",
                        "ostia",
                        "psy4",
                        "mercator_global",
                        "bdpe",
                        "safosi",
                        "safosi_hn",
                        "safosi_hs",
                    ]
                ),
                fields=dict(
                    values=[
                        "sst",
                        "seaice",
                        "ocean",
                        "seaice_conc",
                        "seaice_thick",
                    ]
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "rawfields"

    def olive_basename(self):
        if self.origin == "nesdis" and self.fields == "sst":
            bname = ".".join((self.fields, self.origin, "bdap"))
        elif self.fields == "seaice":
            bname = "ice_concent"
        else:
            bname = ".".join((self.fields, self.origin))
        return bname

    def archive_basename(self):
        if self.origin == "nesdis" and self.fields == "sst":
            bname = ".".join((self.fields, self.origin, "bdap"))
        elif self.fields == "seaice":
            bname = "ice_concent"
        else:
            bname = ".".join((self.fields, self.origin))
        return bname


@namebuilding_insert("radical", lambda s: s.fields)
class GeoFields(GeoFlowResource):
    _footprint = [
        dict(
            info="File containing a limited list of fields in a specific geometry",
            attr=dict(
                kind=dict(values=["geofields"]),
                fields=dict(
                    values=[
                        "sst",
                        "seaice",
                        "ocean",
                        "seaice_conc",
                        "seaice_thick",
                    ]
                ),
                nativefmt=dict(values=["fa"], default="fa"),
            ),
        )
    ]

    @property
    def realkind(self):
        return "geofields"

    def olive_basename(self):
        bname = "icmshanal" + self.fields
        if self.fields == "seaice":
            bname = bname.upper()
        return bname

    def archive_basename(self):
        return "icmshanal" + self.fields
