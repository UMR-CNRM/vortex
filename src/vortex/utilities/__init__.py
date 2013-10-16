#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


def mktuple(obj):
    if isinstance(obj, list) or isinstance(obj, tuple):
        return tuple(obj)
    else:
        return (obj,)


if __name__ == '__main__':
    import doctest
    doctest.testmod() 
