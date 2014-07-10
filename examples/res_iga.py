#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import logging
logging.basicConfig(level=logging.DEBUG)

from vortex import sessions, toolbox

t = sessions.ticket()
t.info()

import vortex.data
import iga.data


def bilan(hdls):
    for hdl in hdls:
        print hdl
        print hdl.complete
        print hdl.provider
        print hdl.provider.pathname(hdl.resource)
        print hdl.resource
        print hdl.resource.as_dict()
        print hdl.container
        print hdl.location()
        hdl.get()

liste_infos_res = (
    dict(kind='analysis', model='arpege', cutoff="assim", date="2011110906",
         file='/ch/mxpt/mxpt001/steph_perso/python/Vortex/SandBox/Essai/ICMSHARPEINIT',
         geometry='france', scheme='file', netloc='oper', user='mxpt001', profile='oper'),
#   dict(kind='matfilter', model='arpege', domain='GLOB15',
#        file='/ch/mxpt/mxpt001/steph_perso/python/Vortex/SandBox/Essai/matrixfil.[domain]',
#        geometry='france', scheme='file', netloc='oper',
#        user='mxpt001', profile='oper'),
#    dict(kind='rtcoef', model='arpege',
#         file='/ch/mxpt/mxpt001/steph_perso/python/Vortex/SandBox/Essai/rtcoef.tar',
#         geometry='france',mode='oper', scheme='file', netloc='oper',
#         user='mxpt001', profile='oper'),
#    dict(kind='namelistfcp', model='arpege',
#         file='/ch/mxpt/mxpt001/steph_perso/python/Vortex/SandBox/Essai/namelistfcp',
#         geometry='france',mode='oper', scheme='file', netloc='oper',
#         user='mxpt001', profile='oper'),
#    dict(kind='namselect', geometry='france', model='arpege',
#         file='/ch/mxpt/mxpt001/steph_perso/python/Vortex/SandBox/Essai/xt.00DDHH00',
#         scheme='file', netloc='oper',user='mxpt001')
    dict(kind='clim_bdap', model='arpege', domain='GLOB15', month=11,
         file='/ch/mxpt/mxpt001/steph_perso/python/Vortex/SandBox/Essai/const.clim.[domain]',
         geometry='france', mode='oper', scheme='file', netloc='oper',
         user='mxpt001', profile='oper'),
    dict(kind='clim_model', model='arpege', truncation=798, month=11,
         domain='GLOB15',
         file='/ch/mxpt/mxpt001/steph_perso/python/Vortex/SandBox/Essai/Const.Clim',
         geometry='france', mode='oper', scheme='file', netloc='oper',
         user='mxpt001', profile='oper'),
)

for elmt in liste_infos_res:
    lh = toolbox.rload(**elmt)
    bilan(lh)

