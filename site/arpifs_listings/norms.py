#!/usr/bin/env python
# -*- coding: utf-8 -*-

__all__ = ['Norm', 'NormComparison', 'compare_norms']

import sys
import collections

from .util import diverging_digit, get_maxint


class Norm(object):
    """
    Handling of fields norms at one time step.
    
    ex:
    - Norm.spnorms: {'TEMPERATURE':'0.256351366366780E+03',
                     ...}
    - Norm.gpnorms: {'TEMPERATURE':{'average':'0.256351366366780E+03',
                                    'minimum': ...}
                     ...}
    """
    def __init__(self, nstep, substep=None):
        """
        **nstep**: number of the time step
        
        **substep**: in case, PREDICTOR or CORRECTOR substep
        """
        self.nstep = nstep
        self.substep = substep
        self.spnorms = {}
        self.gpnorms = {}


class NormComparison(object):
    """
    Handling of the differences between two Norm objects.
    """
    
    def __init__(self, test_norm, ref_norm, only=None):
        """
        **test_norm** and **ref_norm** supposed to be of type Norm.
        
        If **only** among ('spectral', 'gridpoint'), only compare the requested
        type of norms.
        """
        assert isinstance(test_norm, Norm)
        assert isinstance(ref_norm, Norm)
        
        self.test_norm = test_norm
        self.ref_norm = ref_norm
        self.only = only
        
        self._compare()
        
    def _compare(self):
        """Compute comparisons."""
        self.sp_comp, self.gp_comp = compare_norms(self.test_norm,
                                                   self.ref_norm,
                                                   self.only)
    
    def get_worst(self, ntype='both'):
        """
        Get the worst of either 'spectral' or 'gridpoint' norm comparison.
        Or worst of the worst of 'both'.
        """
        if ntype == 'both':
            worst = get_maxint({'spectral':get_maxint(self.sp_comp),
                                'gridpoint':get_maxint(self.gp_comp)})
        elif ntype == 'spectral':
            worst = get_maxint(self.sp_comp)
        elif ntype == 'gridpoint':
            worst = get_maxint(self.gp_comp)
        return worst
    
    def write(self, out=sys.stdout, onlymaxdiff=False):
        """Write the NormComparison to **out**."""
        if len(self.sp_comp) > 0:
            out.write('### SPECTRAL NORMS ###\n')
            out.write('######################\n')
            if not onlymaxdiff:
                _write_normcomp(self.sp_comp, out)
            else:
                _write_normcomp_for_field('Worst norm comparison',
                                          self.get_worst('spectral'),
                                          out)
        if len(self.sp_comp) > 0:
            out.write('### GRIDPOINT NORMS ###\n')
            out.write('######################\n')
            if not onlymaxdiff:
                _write_normcomp(self.gp_comp, out)
            else:
                _write_normcomp_for_field('Worst norm comparison',
                                          self.get_worst('gridpoint'),
                                          out)


###################
# INNER FUNCTIONS #############################################################
###################
def compare_norms(test_norm, ref_norm, only=None):
    """
    Compare norms of two Norm objects.
    If **only** among ('spectral', 'gridpoint'), only compare the requested
    type of norms.
    """
    
    comp_spnorms = collections.OrderedDict()
    comp_gpnorms = collections.OrderedDict()
    if only != 'gridpoint':
        # spnorms
        common_flds = set(test_norm.spnorms.keys()).intersection(set(ref_norm.spnorms.keys()))
        for f in sorted(common_flds):
            comp_spnorms[f] = _compare_spnorm_for(f, test_norm, ref_norm)
    
    if only != 'spectral':
        # gpnorms
        common_flds = set(test_norm.gpnorms.keys()).intersection(set(ref_norm.gpnorms.keys()))
        for f in sorted(common_flds):
            comp_gpnorms[f] = _compare_gpnorm_for(f, test_norm, ref_norm)
    
    return (comp_spnorms, comp_gpnorms)

def _compare_spnorm_for(field, test_norm, ref_norm):
    """Compare spectral norms of two Norm objects for **field**."""
    assert isinstance(test_norm, Norm)
    assert isinstance(ref_norm, Norm)
    return diverging_digit(test_norm.spnorms[field],
                           ref_norm.spnorms[field])

def _compare_gpnorm_for(field, test_norm, ref_norm):
    """Compare gridpoint norms of two Norm objects for **field**."""
    assert isinstance(test_norm, Norm)
    assert isinstance(ref_norm, Norm)
    norms = {}
    for s in ('average', 'minimum', 'maximum'):
        norms[s] = diverging_digit(test_norm.spnorms[field][s],
                                   ref_norm.spnorms[field][s])
    if all([v is None for v in norms.values()]):
        digit = None
    elif '?' in norms.values():
        digit = '?'
    else:
        digit = min([v for v in norms.values() if v is not None])
    return digit

def _write_normcomp_for_field(fieldname, digit, out=sys.stdout):
    """Write **fieldname** and its degree of comparison **digit**."""
    fieldname_width = 30
    digits_len = 2
    arrow = ' --> '
    idupto = 'identical up to {:>{width}} digits'
    unable = '??? unable to compare, check manually ???'
    fmt = arrow + idupto
    fmtlen = len(idupto.format('', width=digits_len))
    if digit is None:
        out.write('{:>{width}}'.format(fieldname, width=fieldname_width) + \
                  ' --> {:=<{width}}'.format('', width=fmtlen))
    elif digit == '?':
        out.write('{:>{width}}'.format(fieldname, width=fieldname_width) + \
                  ' --> {:<{width}}'.format(unable, width=len(unable)))
    else:
        out.write('{:>{width}}'.format(fieldname, width=fieldname_width) + \
                  fmt.format(str(digit), width=digits_len))
    out.write('\n')

def _write_normcomp(comp_norm, out=sys.stdout):
    assert isinstance(comp_norm, dict)
    for f, d in comp_norm.items():
        _write_normcomp_for_field(f, d, out)
