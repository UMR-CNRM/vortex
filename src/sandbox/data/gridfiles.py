"""
TODO: Module documentation
"""

from vortex.data.contents import JsonDictContent, TextContent
from vortex.data.flow import FlowResource
from vortex.syntax.stddeco import namebuilding_insert

from common.data.gridfiles import GridPointExport

#: No automatic export
__all__ = []


class GribInfos(FlowResource):
    """List of available GRIB files with file size and md5sum."""

    _footprint = dict(
        info = 'Available GRIB files with file size and md5sum.',
        attr = dict(
            kind = dict(
                values   = ['gribinfos', ],
            ),
            clscontents = dict(
                default = JsonDictContent,
            ),
            nativefmt   = dict(
                values  = ['json'],
                default = 'json',
            ),
        )
    )

    @property
    def realkind(self):
        return 'gribinfos'


class GridPointExportHashContent(TextContent):
    """Read the hash files properly (ignoring extras spaces...)"""
    pass


@namebuilding_insert('fmt', lambda s: [s.hash_method, s.nativefmt])
class GridPointExportHash(GridPointExport):
    """Store a hash-file associated with a Grib file."""

    _footprint = dict(
        attr = dict(
            nativefmt = dict(
                values = ['ascii']
            ),
            hash_method = dict(
                values = ['md5']
            ),
            clscontents = dict(
                default = GridPointExportHashContent,
            ),
        )
    )
