#!/bin/env python
# -*- coding:Utf-8 -*-

'''
    Eclipse semble ne parser certains sources que quand on les utilise.
    Tout est importé dans ce source, généré par:
       find . -name __init__* \
       | grep -v \.pyc$ \
       | sed -e 's/.__init__.py//' -e 's:./src/:import :' -e 's:/:.:g'
'''

import common
import common.algo
import common.data
import common.tools
import gco
import gco.data
import gco.syntax
import gco.tools
import iga
import iga.data
import iga.syntax
import iga.tools
import iga.utilities
import mercator
import mercator.data
import mercator.syntax
import olive
import olive.data
import sandbox
import sandbox.data
import vortex
import vortex.algo
import vortex.data
import vortex.layout
import vortex.syntax
import vortex.tools
import vortex.utilities
