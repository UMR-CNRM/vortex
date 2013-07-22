#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


def mktuple(obj):
    if isinstance(obj, list) or isinstance(obj, tuple):
        return tuple(obj)
    else:
        return (obj,)

def dictmerge(d1, d2):
    """
    Merge two dictionaries d1 and d2 with a recursive function (d1 and d2 can be dictionaries of dictionaries).
    The result is in d1.
    If keys exist in d1 and d2, d1 keys are replaced by d2 keys.
    
    >>> dictmerge({'name':'clim','attr':{'model':{'values':('arpege','arome')}}},{'name':'clim model','attr':{'truncation':{'type':'int','optional':'False'}}})
    {'name': 'clim model', 'attr': {'model': {'values': ('arpege', 'arome')}, 'truncation': {'optional': 'False', 'type': 'int'}}}

    >>> dictmerge({'a':'1'},{'b':'2'})
    {'a': '1', 'b': '2'}
    
    >>> dictmerge({'a':'1','c':{'d':'3','e':'4'},'i':{'b':'2','f':{'g':'5'}}}, {'c':{'h':'6', 'e':'7'}})
    {'a': '1', 'i': {'b': '2', 'f': {'g': '5'}}, 'c': {'h': '6', 'e': '7', 'd': '3'}}
    """
     
    for key,value in d2.iteritems():
        if type(value) == type(dict()):
            if d1.has_key(key):
                dictmerge(d1[key],d2[key])
            else :
                d1[key] = value
        else:
            d1[key] = value
                  
    return d1

def list2dict(a, klist):
    """
    Convert any list value in a merged dictionary for the specified top entries
    of the ``klist`` from the dictionnary ``a``.
    """

    for k in klist:
        if k in a and type(a[k]) != dict:
            ad = dict()
            for item in a[k]:
                ad.update(item)
            a[k] = ad
    return a
      
            
if __name__ == '__main__':
    import doctest
    doctest.testmod() 
