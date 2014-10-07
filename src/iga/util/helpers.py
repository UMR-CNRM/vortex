#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from vortex.util.config   import GenericConfigParser
from vortex.data.contents import IndexedTable


class IgaHelperSelect(IndexedTable):

    def __init__(self, data=None, filled=False):
        super(IgaHelperSelect, self).__init__(data=data)
        self.parser = IgaHelperParser('helper-namselect.ini')

    def xxtpos(self, n, g, x):
        #g for guess coming from _replacement function
        #x for extras coming from _replacement function
        #obtain the name of the model
        model = g.get('model', x.get('model', None))
        self.add(self.parser.get_info(model))
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

    def xxtselect(self, g, x):
        #0 for the first element of the internal dictionnary
        return self.xxtpos(1, g, x)

    def xxt(self, g, x):
        #1 for the second element of the internal dictionnary
        return self.xxtpos(0, g, x)


class IgaHelperParser(GenericConfigParser):
    """docstring for IgaHelperParser"""

    def get_info(self, current):
        """docstring for get_info"""
        return [
            [ int(option), xxt_select.split()[0], xxt_select.split()[1] ]
            for option, xxt_select in self.items(current)
        ]
