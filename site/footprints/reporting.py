#!/bin/env python
# -*- coding:Utf-8 -*-

"""
Hierarchical documents to store footprints information.
Derived from :class:`xml.dom.minidom.Document`.
"""

#: No automatic export
__all__ = []

from datetime import datetime
from xml.dom.minidom import Document


def reportmap(_reportmap = dict()):
    """Default reporting table."""
    return _reportmap

def reportcopy():
    return reportmap().copy()

def report(tag='default', xmlbase=None):
    """Factory to retrieve a information report document, according to the ``tag`` provided."""
    rtab = reportmap()
    if tag not in rtab:
        rtab[tag] = StandardReport(tag, xmlbase)
    return rtab[tag]


class StandardReport(Document):

    def __init__(self, tag=None, xmlbase=None):
        Document.__init__(self)
        self.root = self.createElement('report')
        self.root.setAttribute('tag', tag)
        self.appendChild(self.root)
        self._current = self.root


    def __call__(self):
        """Print the complete dump of the current report object."""
        print self.dump_all()

    def new_entry(self, kind, name):
        """Insert a top level entry (child of the root node)."""
        entry = self.createElement(str(kind))
        entry.setAttribute('name', name)
        entry.setAttribute('stamp', str(datetime.now()))
        self.root.appendChild(entry)
        return self.root.lastChild

    def add(self, kind, name, base=None, why=None):
        """Add a information node to the ``base`` or current note."""
        if not base:
            base = self.current()
        entry = self.createElement(str(kind))
        entry.setAttribute('name', name)
        if why:
            entry.setAttribute('why', why)
        base.appendChild(entry)
        return base.lastChild

    def current(self, node=None):
        """Return current active node of the document."""
        if node:
            self._current = node
        return self._current

    def dump_all(self):
        """Return a string with a complete formatted dump of the document."""
        return self.toprettyxml(indent='    ')

    def dump_last(self):
        """Return a string with a complete formatted dump of the last entry."""
        return self.root.lastChild.toprettyxml(indent='    ')

    def info(self):
        """Return a simple description as a string."""
        return '{0:s} {1:s}'.format(self.root.tagName, self.root.getAttribute('tag')).title()

    def iter_last(self):
        """Iterate on last node and return ( class, name, why ) information."""
        for kid in self.root.lastChild.childNodes:
            dico = dict(classname=kid.getAttribute('name'))
            for subkid in kid.childNodes:
                dico['name'] = subkid.getAttribute('name')
                dico['why'] = subkid.getAttribute('why')
                yield dico


class FactorizedReport(object):

    def __init__(self, tag, *listofkeys, **kw):
        """
        Generates a report whose items are sorted using some parameters

         - tag is the end-level entry that have to be sorted
         - listofkeys describes the sorting options. It must be a
         list of pair (keyName, interestingValues) where :
             * the order of the list defines the priority order for sorting
             * interestingValues is a tuple of values you want to be signaled first if encountered.
        """
        self.tag = tag
        self._define = dict(listofkeys)
        self._order = [ x[0] for x in listofkeys ]
        self.indent = kw.get('indent', '    ')
        self._tree = dict()

    def get_order(self, dic, depth):
        order = list()
        other = dic.keys()
        for val in self.interestingValues(self.keys()[depth]):
            for v in other:
                if v.startswith(val):
                    order.append(v)
                    other.remove(v)
        order.extend(other)
        return order

    def keys(self):
        return self._define.keys()

    def interestingValues(self, key):
        return self._define[key]

    def add(self, **kw):
        tagValue = kw[self.tag]
        dic = self._tree
        for k in self.keys():
            v = kw.get(k)
            if v not in dic:
                dic[v] = dict()
            dic = dic[v]
        info = kw.get('info', None)
        dic[tagValue] = info

    def printer(self,dic, currentIndent, depth, ordered=False):
        if depth == len(self.keys()):
            for tagValue in dic:
                print currentIndent, self.tag , ':', tagValue,
                if dic[tagValue]:
                    print '(' + dic[tagValue]+')'
                else :
                    print
        else:
            if ordered:
                order = self.get_order(dic, depth)
            else:
                order = dic
            for v in order:
                print currentIndent, self.keys()[depth], '=', v
                self.printer(dic[v],currentIndent+self.indent, depth+1, ordered)


    def softprint(self):
        self.printer(self._tree,self.indent,0)

    def orderedprint(self):
        self.printer(self._tree,self.indent,0, ordered = True)

    def simpleprinter(self,dic, depth, mess=None, space=True):
        if depth == len(self.keys()):
            if space:
                print
            for tagValue in dic:
                print self.indent, self.tag , ':', tagValue,
                if dic[tagValue]:
                    print '(' + dic[tagValue]+')'
                else :
                    print
            if mess:
                print self.indent*3, mess
        else:
            for v in self.get_order(dic, depth):
                if mess:
                    newMess = mess + ' | ' + self.keys()[depth] + ' = ' + v
                else:
                    newMess = self.keys()[depth] + ' = ' + v
                self.simpleprinter(dic[v], depth+1, newMess) 

    def niceprinter(self, dic, depth, maxDepth, group, mess=None, separator='+'):
        if depth == maxDepth:
            self.simpleprinter(dic,depth,mess,depth%group!=0)
        else:
            toPrint=None
            if depth % group == 0:
                toPrint=mess
                mess=None
            if toPrint:
                if separator=='+':
                    separator='-'
                elif separator =='-':
                    separator='~'
            for v in self.get_order(dic, depth):
                if mess:
                    newMess = mess + ' | ' + self.keys()[depth] + ' = ' + v
                else:
                    newMess = self.keys()[depth] + ' = ' + v
                self.niceprinter(dic[v], depth+1, maxDepth, group, newMess, separator)
                if depth % group ==0:
                    print self.indent+(separator*(40+5*len(self.indent)))
            if toPrint:
                print self.indent*((maxDepth-depth)/group + 4), toPrint

    def dumper(self,maxDepth=1, group=1):
        if maxDepth > len(self.keys()):
            maxDepth = len(self.keys())
        self.niceprinter(self._tree, 0, maxDepth, group)

if __name__ == '__main__':
    fr = FactorizedReport(
        'classname',
        ('name', ('kind', 'date')),
        ('why', ('Missing value', 'Not valid', 'Not in values', 'Outcast value')),
        indent = '   '
    )

    fr.add(classname='toto',name='kind',why='Not Valid', info='blabla')
    fr.add(classname='tata',name='kind',why='Invalid')
    fr.add(classname='tata2',name='kind',why='Invalid', info = 'idem')
    fr.add(classname='grosMinet',name='date',why='Not in values : test', info='values = [today, 20130807]')
    fr.add(classname='titi', name='date', why = 'Missing value')
    fr.add(classname='tutu',name='bidon',why='Invalid')
    fr.add(classname='tyty',name='aa',why='n\'importe quoi ' )

    fr.orderedprint()

    print
    print '=======================new Version========================'
    print
    fr.dumper()

    print
    print '=======================new Version bis========================'
    print
    fr.dumper(maxDepth=2)
