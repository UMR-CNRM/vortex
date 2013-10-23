#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex
from vortex.data.contents import IndexedTable

import common.data
import olive.data
import gco.data
import gco.syntax

from gco.tools import genv 

t = vortex.ticket()
g = t.glove
rl = vortex.toolbox.rload

print t.line

print t.prompt, 'Playing with table and callable attributes'

print t.line

class TablePerso(IndexedTable):
    def xxtpos(self, n, g, x):
        t = g.get('term', x.get('term', None))
        if t is None:
            return None
        else:
            t = int(t)
            if t in self:
                try:
                    value = self[t][n]
                except IndexError:
                    return None
                return value
            else:
                return None
    
    def xxtnam(self, g, x):
        return self.xxtpos(0, g, x)
    
    def xxtsrc(self, g, x):
        return self.xxtpos(1, g, x)

ttab = TablePerso()
ttab.add([
    [0, 'xxt00', 'select0'],
    [1, 'xxt01', 'select0'],
    [2, 'xxt02', 'select0'],
    [3, 'xxt03', 'select3'],
])

arpege_cycle = 'cy36t1_op2.16'

genv.register(
    # current arpege cycle
    cycle=arpege_cycle,
    # a shorthand to acces this cycle
    entry='double',
    # items to be defined
    MASTER_ARPEGE='cy36t1_masterodb-op2.12.SX20r411.x.exe',
    RTCOEF_TGZ='var.sat.misc_rtcoef.12.tgz',
    CLIM_ARPEGE_T798='clim_arpege.tl798.02',
    CLIM_DAP_GLOB15='clim_dap.glob15.07',
    MAT_FILTER_GLOB15='mat.filter.glob15.07',
    NAMELIST_ARPEGE='cy36t1_op2.11.nam'
)

print genv.cycles()

print t.line

nams = rl(
    genv=arpege_cycle,
    role = 'SelectionNamelist',
    kind = 'namselect',
    source='[helper::xxtsrc]',
    term = (0,3),
    local = '[helper::xxtnam]',
    helper = ttab,
)

for n in nams:
    print t.line, n.idcard()

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line
