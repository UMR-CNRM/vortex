#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


from vortex.data.executables import NWPModel
from gco.syntax.stdattrs import GenvKey

from vortex.utilities.decorators import printargs


class IFSModel(NWPModel):
    """Yet an other IFS Model."""
    
    _footprint = dict(
         info = 'IFS Model',
        attr = dict(
            gvar = dict(
                type = GenvKey,
                optional = True,
                default = 'master_[model]'
            ),
            kind = dict(
                values = [ 'ifsmodel', 'mfmodel', 'aaa' ]
            )
        )
    )

    @classmethod
    def realkind(cls):
        return 'ifsmodel'

    def iga_pathinfo(self):
        return dict(
            model = self.model
        )

    def iga_basename(self):
        return 'ARPEGE'

    @printargs
    def rootcmdline(self, model=None, vmodel='meteo', name='XPVT', conf=1, timescheme='sli', timestep=600, fcterm=0, fcunit='h'):
        if model:
            return '-v{0:s} -e{1:s} -c{2:d} -a{3:s} -t{4:d} -f{5:s}{6:d} -m{7:s}'.format(
            vmodel, name, conf, timescheme, timestep, fcunit, fcterm, model)
        else:
            return '-v{0:s} -e{1:s} -c{2:d} -a{3:s} -t{4:d} -f{5:s}{6:d}'.format(
            vmodel, name, conf, timescheme, timestep, fcunit, fcterm)

