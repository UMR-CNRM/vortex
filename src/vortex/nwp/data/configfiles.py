"""
Various configuration files (Namelists excepted).
"""

from vortex.data.outflow import StaticResource
from ..syntax.stdattrs import gvar
from vortex.data.contents import JsonDictContent, DataRaw
from vortex.syntax.stddeco import namebuilding_append

#: No automatic export
__all__ = []


@namebuilding_append("src", lambda self: [self.scope, self.source])
class GenericConfig(StaticResource):
    """Generic class to access a pack of configuration files."""

    _abstract = True
    _footprint = [
        gvar,
        dict(
            info="Configuration file from a pack",
            attr=dict(
                kind=dict(values=["config"]),
                gvar=dict(default="config_[scope]"),
                scope=dict(info="The configuration pack purpose"),
                source=dict(
                    info="The config name within the config pack.",
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "config"

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return "extract=" + self.source


class AsciiConfig(GenericConfig):
    """Generic class to access a pack of ASCII configuration files."""

    _footprint = dict(
        info="ASCII Configuration file from a pack",
        attr=dict(
            nativefmt=dict(
                values=[
                    "ascii",
                ]
            ),
            clscontents=dict(default=DataRaw),
        ),
    )


class IniConfig(GenericConfig):
    """Generic class to access a ini configuration file (e.g. for mkjob)."""

    _footprint = dict(
        info="Ini configuration file",
        attr=dict(
            nativefmt=dict(
                values=[
                    "ini",
                ]
            ),
        ),
    )


class JsonConfig(GenericConfig):
    """Generic class to access a pack of JSON configuration files."""

    _footprint = dict(
        info="JSON Configuration file from a pack",
        attr=dict(
            scope=dict(
                outcast=[
                    "oops",
                ]
            ),
            nativefmt=dict(
                values=[
                    "json",
                ]
            ),
            clscontents=dict(default=JsonDictContent),
        ),
    )


class OopsJsonConfig(JsonConfig):
    """Configuration files for OOPS, defining the oops objects to be built"""

    _footprint = dict(
        info="OOPS JSON Configuration file from a pack",
        attr=dict(
            scope=dict(
                values=[
                    "oops",
                ],
                outcast=[],
            ),
            objects=dict(
                info="The OOPS objects to be built.",
            ),
            source=dict(
                info="The config name within the config pack.",
                optional=True,
                default="[objects].json",
            ),
        ),
    )


class YamlConfig(GenericConfig):
    """Generic class to access a pack of YAML configuration files."""

    _footprint = dict(
        info="YAML Configuration file from a pack",
        attr=dict(
            nativefmt=dict(
                values=[
                    "yaml",
                ]
            ),
        ),
    )


class Bundle(StaticResource):
    """Contains bundling of source codes."""

    _footprint = [
        gvar,
        dict(
            info="Contains bundling of source codes.",
            attr=dict(
                kind=dict(values=["bundle"]),
                gvar=dict(
                    default="bundle",
                ),
                nativefmt=dict(values=["yml", "yaml"]),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "bundle"
