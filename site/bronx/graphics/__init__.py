#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
*graphics* sub-module:

Graphical tools.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import numpy
import copy
import matplotlib
import datetime

import footprints.loggers

logger = footprints.loggers.getLogger(__name__)

#: No automatic export
__all__ = []


def read_cmap(sourcefile):
    """
    Read and creates a custom Colormap from a set of RGB colors in a file with the
    following formating:

    r1,g1,b1;\n
    r2,g2,b2;\n
    ...\n
    rn,gn,bn

    each value being comprised between 0 and 255, or 0 and 1.

    :param sourcefile: open file-like object to read colormap in.
    """
    colors = sourcefile.readlines()
    for i in range(len(colors)):
        colors[i] = colors[i].replace(';', '')
        colors[i] = colors[i].replace('[', '')
        colors[i] = colors[i].replace(']', '')
        colors[i] = colors[i].replace('\n', '')
        colors[i] = colors[i].split(',')
    colors = numpy.array(colors, dtype=numpy.float64)
    if colors.max() > 1.:
        colors /= 255.
    return matplotlib.colors.ListedColormap(colors)


def add_cmap(cmap, sourcefile):
    """
    Reads and registers the given colormap in matplotlib.

    :param cmap: name of the colormap, to be registered under and used then
    :param sourcefile: file-like object to read the colormap in.
    """
    plt = matplotlib.pyplot
    if cmap not in plt.colormaps():
        plt.register_cmap(name=cmap,
                          cmap=read_cmap(sourcefile))
    else:
        raise ValueError('this colormap is already registered: {}'.format(cmap))


def get_norm4colorscale(scaling, max_val=None):
    """
    Creates a matplotlib.colors.BoundaryNorm object tuned for scaled colormaps,
    i.e. discrete, irregular colorshades.

    :param scaling: the values determining changes of colors
    :param max_val: an additional maximum value to replace the upper bound if
                    this value is included between the last two upper values.

    :return: a tuple (norm, scaling), scaling being eventually modified
             according to **max_val**
    """
    colors = matplotlib.colors
    bounds = copy.copy(scaling)
    if max_val is not None:
        if bounds[-2] <= max_val <= bounds[-1]:
            bounds[-1] = max_val
    norm = colors.BoundaryNorm(boundaries=bounds, ncolors=len(bounds) - 1)
    return (norm, bounds)


def set_figax(figure=None, ax=None,
              **subplots_kw):
    """
    Generate or check consistency of (**figure**, **ax**) duet to work on.

    If **figure** and **ax** are both *None*, generate the duet
    using pyplot.subplots(), in which case any argument can be additionally
    passed through subplots_kw.
    """
    plt = matplotlib.pyplot
    if ax is not None and figure is None:
        figure = ax.figure
    elif ax is None and figure is not None:
        if len(figure.axes) > 0:
            ax = figure.axes[0]
        else:
            ax = figure.gca()
    elif ax is not None and figure is not None:
        if ax not in figure.axes:
            raise ('*over*: inconsistency between given fig and ax')
    elif figure is ax is None:
        figure, ax = plt.subplots(**subplots_kw)
    return (figure, ax)


def set_nice_time_axis(axis, xy,
                       dt_min=None, dt_max=None,
                       showgrid=True,
                       datefmt=None,
                       tickslabelsrotation=30.):
    """
    Set an adequate axis ticks and ticks labels for Date/Hour axis.

    :param axis: the axis instance to work on
    :param xy: must be 'x' or 'y'
    :param dt_min: datetime.datetime instance corresponding to plot min;
                   if None, take it from axis
    :param dt_max: datetime.datetime instance corresponding to plot max
                   if None, take it from axis
    :param showgrid: to set the grid or not
    :param datefmt: format for date
    :param tickslabelsrotation: angle in degrees, anti-clockwise order
    """
    mdates = matplotlib.dates
    plt = matplotlib.pyplot

    if xy == 'x':
        z_min = axis.axis()[0]
        z_max = axis.axis()[1]
    elif xy == 'y':
        z_min = axis.axis()[2]
        z_max = axis.axis()[3]
    if dt_min is None:
        dt_min = mdates.date2num(z_min)
    if dt_max is None:
        dt_max = mdates.date2num(z_max)
    datetimerange = dt_max - dt_min

    dayhourformatter = mdates.DateFormatter('%Y-%m-%d\n%H:%M:%S')
    dayformatter = mdates.DateFormatter('%Y-%m-%d')
    if datetimerange <= datetime.timedelta(2):
        major_locator = mdates.HourLocator(interval=6)
        minor_locator = mdates.HourLocator(interval=1)
        formatter = mdates.AutoDateFormatter(major_locator)
    elif datetimerange <= datetime.timedelta(7):
        major_locator = mdates.DayLocator(interval=1)
        minor_locator = mdates.HourLocator(interval=6)
        formatter = dayhourformatter
    elif datetimerange <= datetime.timedelta(21):
        major_locator = mdates.DayLocator(interval=2)
        minor_locator = mdates.DayLocator(interval=1)
        formatter = dayhourformatter
    elif datetimerange <= datetime.timedelta(100):
        major_locator = mdates.DayLocator(interval=7)
        minor_locator = mdates.DayLocator(interval=1)
        formatter = dayformatter
    else:
        major_locator = mdates.AutoDateLocator()
        minor_locator = None
        formatter = mdates.AutoDateFormatter(major_locator)
    if datefmt is not None:
        formatter = mdates.DateFormatter(datefmt)
    if xy == 'x':
        myaxis = axis.xaxis
    else:
        myaxis = axis.yaxis
    myaxis.set_major_locator(major_locator)
    myaxis.set_major_formatter(formatter)
    axis.grid(showgrid)
    if minor_locator is not None:
        myaxis.set_minor_locator(minor_locator)
        axis.grid(showgrid, which='minor', axis=xy, color='grey')
    if tickslabelsrotation != 0.:
        _ax = plt.gca()
        plt.sca(axis)
        if xy == 'x':
            plt.xticks(rotation=tickslabelsrotation)
        else:
            plt.yticks(rotation=tickslabelsrotation)
        plt.sca(_ax)
