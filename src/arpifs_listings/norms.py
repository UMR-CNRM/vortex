"""
Module that deals with part of the Arpege/IFS listings related to the
spectral norms of model or post-processing fields.
"""

import sys
import collections
import re

from .util import (read_listing,
                   number_of_different_digits,
                   find_line_containing,
                   re_for_fortran_scientific_format,
                   re_for_nan,
                   ParsingError,
                   PARSING_ERROR_CODE,
                   FOUND_NAN_ERROR_CODE,
                   get_worst)

#: Automatic export
__all__ = ['Norms', 'NormsComparison', 'compare_norms']

patterns = {'spectral norms': 'SPECTRAL NORMS -',
            'gpnorms partA': 'GPNORM',
            'gpnorms partB': 'GPNORMS OF FIELDS TO BE WRITTEN OUT ON FILE :',
            'fullpos gpnorms': 'FULL-POS GPNORMS',
            'gpnorms partA complete': re.compile(r'GPNORM (?P<fld>.*)\s+AVERAGE\s+MINIMUM\s+MAXIMUM\s*$')
            }
_re_openfa = r'(?P<subroutine>OPENFA)'
_re_cnt34 = r'(?P<subroutine>CNT[3-4]((TL)|(AD))*)'
_re_comment = r'(?P<comment>(\s\w+)+)'
_re_unit = r'(?P<unit>\d+)'
_re_filename = r'(?P<filename>(\w|\+)+)'
_re_nstep = r'(?P<nstep>\d+)'
_re_stepo = r'(?P<subroutine>STEPO((TL)|(AD)|(_OOPS))*)'
_re_scan2m = r'(?P<subroutine>SCAN2M((TL)|(AD))*)'
_re_nsim4d = r'(?P<nsim4d>\d+)'
_re_cdconf = r'(?P<cdconf>\w+)'
_re_pcstep = r'(\((?P<pc_step>(PREDICTOR)|(CORRECTOR))\)\s+)?'
_re_dfi = r'(?P<dfi>DFI STEP)'
_re_dfistep = r'(?P<dfi_step>(\+|\-)\d+\/\s*\d+)'
_re_model_init = r'(?P<subroutine>MODEL_INIT:(BEFORE)|(AFTER) TRANSDIRH_FROM_T0)'
_re_fields_oops = r'(?P<subroutine>field:(copy (rhs)|(self))|(interp in))'
_re_fields_oopsIFS = r'(?P<subroutine>FieldsIFS)'
_re_ifs_propagate = r'(?P<subroutine>ifs_propagate_c)'
_re_wrmlppa = r'(?P<subroutine>WRMLPPA)'
_re_sugridf = r'(?P<subroutine>SUGRIDF)'
_re_sugridug = r'(?P<subroutine>SUGRIDUG)'
CNT_steps = {'openfa_info': r'\s*' + _re_openfa + r':' + _re_comment + r'\s*$',
             'openfa': r'\s*' + _re_openfa + r':\s+' + _re_unit + r'\s+' + _re_filename + r'\s*$',
             'nstep_stepo': r'\s*NSTEP =\s+' + _re_nstep + r'\s+' + _re_stepo + r'\s+' + _re_cdconf + r'\s*$',
             'nstep_scan2m': r'\s*NSTEP =\s+' + _re_nstep + r'\s+' + _re_scan2m + r'\s+' + _re_cdconf + r'\s*$',
             'norms_at_nstep': r'\s*NORMS AT NSTEP\s+' + _re_cnt34 + r'\s+' + _re_pcstep + _re_nstep + r'\s*$',
             'norms_at_nstep_oops': r'\s*NORMS AT NSTEP\s+' + _re_nstep + r'\s*$',
             'start_cnt4_nsim4d': r'\s*START\s+' + _re_cnt34 + r', NSIM4D=\s+' + _re_nsim4d + r'\s*$',
             'end_cnt3': r'\s*END\s+' + _re_cnt34 + r'\s*$',
             'dfi_step': r'\s*(\d|:)*\s+' + _re_dfi + r'\s+' + _re_dfistep + r'\s*\+CPU=.*\s*$',
             'model_init': r'\s*' + _re_model_init + r'\s*$',
             'fields_oops': r'\s*' + _re_fields_oops + r'\s*$',
             'fields_oopsIFS': r'\s*' + _re_fields_oopsIFS + r'\s*$',
             'ifs_propagate_oops': r'\s*' + _re_ifs_propagate + r'\s*1\s*$',
             'wrmlppa': r'\s*' + _re_wrmlppa + r'\s+NSTEP=\s+' + _re_nstep + r'\s+CDCONF=' + _re_cdconf + r'\s*$',
             'sugridf': r'\s*' + _re_sugridf + r'\s*:\s*' + _re_comment + r'\s*$',
             'sugridug': r'\s*' + _re_sugridug + r'\s*:\s*' + _re_comment + r'\s*$',
             }
CNT_steps = {k: re.compile(v) for k, v in CNT_steps.items()}


class NormsSet:
    """
    Handling several Norm objects at different steps.
    """

    def __init__(self, source=None, from_list=None):
        """
        :param source: may be either a filename or a list of lines.
        :param from_list: to be passed to constructor :meth:`from_list()`
        """
        self.norms_at_each_step = []
        self.steps_linerecord = []
        if source is not None:
            self._parse_listing(source)
        elif from_list is not None:
            self.from_list(from_list)

    def from_list(self, list_of_Norms):
        """Initialize from a list of Norms object."""
        self.norms_at_each_step = list_of_Norms

    def __getitem__(self, item):
        return self.norms_at_each_step[item]

    def __len__(self):
        return len(self.norms_at_each_step)

    def __iter__(self):
        yield from self.norms_at_each_step

    def __eq__(self, other):
        return (len(self) == len(other) and
                all([self.norms_at_each_step[i] == other.norms_at_each_step[i]
                     for i in range(len(self))])
                )

    def pop(self, i):
        self.norms_at_each_step.pop(i)
        self.steps_linerecord.pop(i)

    def steps(self):
        return [self.norms_at_each_step[i].step for i in range(len(self))]

    def steps_equal(self, other):
        """Check if all of the steps in self are equals to the one in other."""
        return (len(self) == len(other) and
                all([self.norms_at_each_step[i].step == other.norms_at_each_step[i].step
                     for i in range(len(self))])
                )

    def _parse_listing(self, source):
        """
        Parse a listing (either given as its filename or already read as a
        list of lines) looking for norms.
        """
        lines = read_listing(source)
        # find CNT steps
        steps = []
        for i, l in enumerate(lines):
            for v in CNT_steps.values():
                _re = v.match(l)
                if _re:
                    s = _re.groupdict()
                    s['line'] = _re.string
                    s['lineno'] = i
                    steps.append(s)
                    break
        nsim4d = None
        nstep = None
        subroutine = None
        # fill missing values with those found before
        for s in steps:
            nsim4d = s.get('nsim4d', nsim4d)
            nstep = s.get('nstep', nstep)
            subroutine = s.get('subroutine', subroutine)
            s['nsim4d'] = nsim4d
            s['nstep'] = nstep
            s['subroutine'] = subroutine

        # look for norms at each step
        for i in range(len(steps)):
            lineno = steps[i].pop('lineno')
            i0 = lineno
            if i == len(steps) - 1:  # last one
                i1 = None
            else:
                i1 = steps[i + 1]['lineno']
            extract = lines[i0:i1]
            norm = Norms(steps[i], extract)
            if not norm.empty:
                self.norms_at_each_step.append(norm)
                self.steps_linerecord.append(lineno)


class Norms:
    """
    Handling of fields norms at one moment/step.
    """

    def __init__(self, step, lines=None, from_dict=None):
        """
        :param step: identification of the step of norms printing
        :param lines: list of lines from readlines() in which to parse
        :param from_dict: passed to constructor :meth:`from_dict(**from_dict)`
        """
        self.step = step
        self.spnorms = {}
        self.gpnorms = {}
        if lines is not None:
            self._parse_norms(lines)
        elif from_dict is not None:
            self.from_dict(**from_dict)

    def from_dict(self, step, spnorms, gpnorms):
        """Initialize from a series of dict for each attribute."""
        self.step = step
        self.spnorms = spnorms
        self.gpnorms = gpnorms

    def as_dict(self):
        """Return this entry data as a dictionary."""
        return {'step': self.step,
                'spnorms': self.spnorms,
                'gpnorms': self.gpnorms}

    @property
    def empty(self):
        """Return True if no norm has been found."""
        return self.spnorms == self.gpnorms == {}

    @property
    def found_NaN(self):
        """Return whether NaN are present in the listing."""
        return (any([re_for_nan.match(str(v)) for v in self.spnorms.values()]) or
                any([re_for_nan.match(str(v)) for v in self.gpnorms.values()]))

    def format_step(self, complete=False):
        """Return a formatted string describing the step."""
        if complete:
            line = ''
            for k in sorted(self.step.keys()):
                line += '{}: {}\n'.format(k, self.step[k])
            line.rstrip('\n')
        else:
            if self.step.get('dfi'):
                line = '{}={}'.format(self.step.get('dfi'),
                                      self.step.get('dfi_step'))
            else:
                line = '(NSIM4D={}, subroutine={}, NSTEP={}'.format(self.step['nsim4d'],
                                                                    self.step['subroutine'],
                                                                    self.step['nstep'])
                if 'cdconf' in self.step.keys():
                    line += ', CDCONF={})'.format(self.step['cdconf'])
                elif 'pc_step' in self.step.keys():
                    line += ' ({}))'.format(self.step['pc_step'])
                elif 'filename' in self.step.keys():
                    line += ', FILENAME={})'.format(self.step['filename'])
                else:
                    line += ')'
        return line

    def _parse_norms(self, lines):
        self._parse_spectral_norms(lines)
        self._parse_gridpoint_norms(lines)

    def _parse_spectral_norms(self, lines):
        """Parse spectral norms from the subset of lines of the listing."""
        (index, line) = find_line_containing(patterns['spectral norms'], lines)
        if index is not None:  # check that the header for spectral norms is found
            lines = lines[index:index + 5]
            for fld in ('LOG(PREHYDS)', 'OROGRAPHY', 'VORTICITY', 'DIVERGENCE',
                        'TEMPERATURE', 'KINETIC ENERGY', 'LOG(PRE/PREHYD)',
                        'd4 = VERT DIV + X', 'HUMIDITY'):
                (idx, line) = find_line_containing(fld, lines)
                if idx is not None:  # fld is found
                    line = line.split()
                    if fld in ('LOG(PREHYDS)', 'OROGRAPHY'):
                        # special case syntax, in line: LOG(PREHYDS)    0.114714299839506E+02
                        val = line[line.index(fld) + 1]
                    else:  # other fields, line below
                        if lines[idx + 1].split()[0] != 'AVE':
                            print(lines[idx])
                            print(lines[idx + 1])
                            raise NotImplementedError('spectral norms level by level.')
                        else:
                            # .split()[0] necessary for KINETIC ENERGY
                            val = lines[idx + 1].split()[line.index(fld.split()[0])]
                    self.spnorms[fld] = val

    def _parse_gridpoint_norms(self, lines):
        """Parse gridpoint norms from the subset of lines of the listing."""
        self._parse_gridpoint_normsA(lines)
        self._parse_gridpoint_normsB(lines, patterns['gpnorms partB'])
        self._parse_gridpoint_normsB(lines, patterns['fullpos gpnorms'])

    def _parse_gridpoint_normsA(self, lines):
        """
        Parse gridpoint norms (syntax A) from the subset of lines of the
        listing.
        Only first (AVE) line is parsed.
        <
         GPNORM INPRRTOT3D           AVERAGE               MINIMUM               MAXIMUM
         AVE   0.000000000000000E+00 0.000000000000000E+00 0.000000000000000E+00
        >
        or
        <
         VCLIA
         GPNORM OUTPUT               AVERAGE               MINIMUM               MAXIMUM
                 AVE   0.284677941566266E-01 0.708309967491275E-04 0.383371754876028E+00
                     1 0.479979959947617E-02 0.227016440704539E-03 0.156422521457101E-01
                     2 0.472130217943848E-01 0.288189754479976E-02 0.162924497411374E+00
                     3 0.444286625411190E-02 0.708309967491275E-04 0.330966742800443E-01
                     4 0.574154889785337E-01 0.458164762144005E-03 0.383371754876028E+00
        >
        """
        start = 0
        sub_extract = lines
        while True:
            sub_extract = sub_extract[start:]
            (idx, line) = find_line_containing(patterns['gpnorms partA'], sub_extract)
            match = patterns['gpnorms partA complete'].match(line.strip())
            if idx is not None and match:
                # signature of part A with field name
                fld = match.group('fld').strip()
                if fld == 'OUTPUT':
                    # name is on the above line
                    fld = sub_extract[idx - 1].strip()
                if fld == 'SOILB   3 FIELDS':
                    # dirty fix
                    for ii in range(1, 4):
                        fldii = fld + ' ({}/3)'.format(ii)
                        vals = {'average': sub_extract[idx + 1 + (ii - 1) * 3].split()[1],
                                'minimum': sub_extract[idx + 1 + (ii - 1) * 3].split()[2],
                                'maximum': sub_extract[idx + 1 + (ii - 1) * 3].split()[3]}
                        self.gpnorms[fldii] = vals
                    start = idx + 1 + 6
                else:
                    # regular
                    vals = {'average': sub_extract[idx + 1].split()[1],
                            'minimum': sub_extract[idx + 1].split()[2],
                            'maximum': sub_extract[idx + 1].split()[3]}
                    start = idx + 1
                    self.gpnorms[fld] = vals
            else:
                break

    def _parse_gridpoint_normsB(self, lines, pattern):
        """
        Parse gridpoint norms (syntax B) from the subset of lines of the
        listing.
        <
         **pattern**
                                           AVERAGE               MINIMUM               MAXIMUM
         SURFTEMPERATURE /FRANX01 : 0.282008581801065E+03 0.264749393516486E+03 0.293120673364284E+03
         >
        """
        re_float = re_for_fortran_scientific_format.pattern
        re_pattern = re.compile(r'\s+(?P<fldname>([\w\.\/\s])+) :' +
                                r' (?P<ave>' + re_float + ')' +
                                r' (?P<min>' + re_float + ')' +
                                r' (?P<max>' + re_float + ')' + '$')
        start = 0
        sub_extract = lines
        while True:
            sub_extract = sub_extract[start:]
            (idx, _) = find_line_containing(pattern, sub_extract)
            if idx is not None:
                idx += 2
                while idx < len(sub_extract):
                    re_ok = re_pattern.match(sub_extract[idx])
                    if re_ok:
                        fld = re_ok.group('fldname').rstrip()
                        vals = {'average': re_ok.group('ave'),
                                'minimum': re_ok.group('min'),
                                'maximum': re_ok.group('max')}
                        self.gpnorms[fld] = vals
                        idx += 1
                    else:
                        break
                start = idx
            else:
                break

    def __eq__(self, other):
        return all([getattr(self, a) == getattr(other, a)
                    for a in ('step', 'spnorms', 'gpnorms')])


class NormsComparison:
    """
    Handling of the differences between two Norm objects.
    """

    def __init__(self, test_norm, ref_norm, only=None, hide_equal_norms=False):
        """

        **test_norm** and **ref_norm** supposed to be of type Norm.

        If **only** among ('spectral', 'gridpoint'), only compare the requested
        type of norms.
        """
        assert isinstance(test_norm, Norms)
        assert isinstance(ref_norm, Norms)

        self.test_norm = test_norm
        self.ref_norm = ref_norm
        self.only = only
        self.hide_equal_norms = hide_equal_norms

        self._compare()

    def _compare(self):
        """Compute comparisons."""
        self.sp_comp, self.gp_comp = compare_norms(self.test_norm,
                                                   self.ref_norm,
                                                   self.only,
                                                   self.hide_equal_norms)

    def get_worst(self, ntype='both'):
        """
        Get the worst of either 'spectral' or 'gridpoint' norm comparison.
        Or worst of the worst of 'both'.
        """
        if ntype == 'both':
            all_ = list(self.sp_comp.values()) + list(self.gp_comp.values())
        elif ntype == 'spectral':
            all_ = list(self.sp_comp.values())
        elif ntype == 'gridpoint':
            all_ = list(self.gp_comp.values())
        return get_worst(all_)

    def write(self, out=sys.stdout, onlymaxdiff=False):
        """Write the NormsComparison to **out**."""
        if len(self.sp_comp) > 0:
            out.write('### SPECTRAL NORMS ###\n')
            out.write('######################\n')
            if not onlymaxdiff:
                _write_normcomp(self.sp_comp, out)
            else:
                _write_normcomp_for_field('Worst norm comparison',
                                          self.get_worst('spectral'),
                                          out)
        if len(self.gp_comp) > 0:
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
def compare_normsets(test, ref, mode,
                     which='first_and_last_spectral',
                     out=sys.stdout,
                     onlymaxdiff=False,
                     hide_equal_norms=False,
                     plot_out='norms_diff.png'):
    """
    Compare 2 Normset objects.

    :param which: either 'all' to compare norms for all steps found in listings,
                  or 'first_and_last_spectral' (default) for the first and last
                  spectral norms only.
    :param out: output open file or stdout
    :param onlymaxdiff: only max difference is printed for each step.
    :param mode: - if 'text', prints the comparison to file;
                 - if 'get_worst_by_step', get worst (among fields) digits
                   comparison for each step;
                 - if 'get_worst' get worst of worst (among fields) digits
                   comparison.
                 - if 'plot', plot a graph of differences
    :param plot_out: if mode == 'plot', name of the plot output file
    """
    if not test.steps_equal(ref):
        st = {n.format_step() for n in test}
        sr = {n.format_step() for n in ref}
        stepset = st.intersection(sr)
        test_rm = [i for i in range(len(test))
                   if test[i].format_step() not in stepset]
        for off, i in enumerate(test_rm):
            test.pop(i - off)
        ref_rm = [i for i in range(len(ref))
                  if ref[i].format_step() not in stepset]
        for off, i in enumerate(ref_rm):
            ref.pop(i - off)
        assert test.steps_equal(ref)
    if which == 'first_and_last_spectral':
        for i in range(len(test)):
            if len(test[i].spnorms) > 0:
                steps = (i, None)
                break
        for i in sorted(range(len(test)), reverse=True):
            if len(test[i].spnorms) > 0:
                steps = (steps[0], i)
                break
        if steps[0] == steps[1]:
            steps = (steps[0],)
    elif which == 'all':
        steps = list(range(len(test)))

    if 'get_worst' in mode:
        worstdigits = []
    elif mode == 'plot':
        normsout = collections.OrderedDict()
    for i in steps:
        norm_comp = NormsComparison(test[i],
                                    ref[i],
                                    hide_equal_norms=hide_equal_norms)
        if mode == 'text':
            if hide_equal_norms and norm_comp.get_worst() == 0:
                continue
            else:
                out.write(test.norms_at_each_step[i].format_step() + '\n')
                norm_comp.write(out, onlymaxdiff)
                out.write('-' * 80 + '\n')
        elif 'get_worst' in mode:
            assert onlymaxdiff is True
            worstdigits.append(norm_comp.get_worst('both'))
        elif mode == 'plot':
            norm_comp = NormsComparison(test.norms_at_each_step[i],
                                        ref.norms_at_each_step[i],
                                        only='spectral')
            if len(norm_comp.sp_comp) > 0:
                normsout[test[i].format_step()] = norm_comp.sp_comp
    if mode == 'plot':
        import matplotlib.pyplot as plt
        fldset = []
        for n in normsout.values():
            fldset.extend(n.keys())
        fldset = sorted(set(fldset))
        tab_f = {f: [n.get(f, None) for n in normsout.values()] for f in fldset}
        xlabels = [(i, f) for i, f in enumerate(normsout.keys())]
        xlen = len(xlabels)
        tn = 5
        if xlen > tn:
            xstep = xlen // tn
            xlast = xlabels[-1]
            xlabels = xlabels[::xstep]
            if (xlast[0] - xlabels[-1][0]) < xstep / 2:
                xlabels[-1] = xlast
            else:
                xlabels.append(xlast)
        fig, axes = plt.subplots(len(fldset), 1, figsize=(12, 8))
        for j, f in enumerate(fldset):
            axes[j].plot(tab_f[f], color='DarkMagenta')
            axes[j].scatter(0, tab_f[f][0], c='DarkMagenta', s=50, marker='o')
            axes[j].set_xlim(0, xlen)
            axes[j].scatter(xlen - 1, tab_f[f][xlen - 1], c='DarkMagenta', s=20, marker='o', edgecolors='face')
            axes[j].set_xticks([x[0] for x in xlabels])
            axes[j].set_xticklabels([])
            axes[j].set_ylim(0, 15)
            axes[j].set_yticks([0, 5, 10, 15])
            axes[j].set_yticklabels([0, 5, 10, 15])
            axes[j].set_ylabel(f, rotation=45., horizontalalignment='right')
            axes[j].grid()
        xlabels = [x[1].split() for x in xlabels]
        for x in xlabels:
            if len(x) > 2:
                x.insert(2, '\n')
        axes[-1].set_xticklabels([''.join(x) for x in xlabels],
                                 rotation=45., horizontalalignment='right')
        axes[0].set_title('Norms: number of # digits')
        print('=> Output in: ' + plot_out)
        fig.savefig(plot_out, bbox_inches='tight', dpi=300)

    if mode == 'get_worst':
        return get_worst(worstdigits)
    elif mode == 'get_worst_by_step':
        return worstdigits
    else:
        return None


def compare_norms(test_norm, ref_norm, only=None, hide_equal_norms=False):
    """Compare norms of two Norms objects.

    If **only** among ('spectral', 'gridpoint'), only compare the requested
    type of norms.
    """
    comp_spnorms = collections.OrderedDict()
    comp_gpnorms = collections.OrderedDict()
    if only != 'gridpoint':
        # spnorms
        common_flds = set(test_norm.spnorms.keys()).intersection(set(ref_norm.spnorms.keys()))
        for f in sorted(common_flds):
            try:
                comp = _compare_spnorm_for(f, test_norm, ref_norm)
            except ParsingError:
                comp = PARSING_ERROR_CODE
            if hide_equal_norms and comp == 0:
                pass
            else:
                comp_spnorms[f] = comp

    if only != 'spectral':
        # gpnorms
        common_flds = set(test_norm.gpnorms.keys()).intersection(set(ref_norm.gpnorms.keys()))
        for f in sorted(common_flds):
            try:
                comp = _compare_gpnorm_for(f, test_norm, ref_norm)
            except ParsingError:
                comp = PARSING_ERROR_CODE
            if hide_equal_norms and comp == 0:
                pass
            else:
                comp_gpnorms[f] = comp

    return (comp_spnorms, comp_gpnorms)


def _compare_spnorm_for(field, test_norm, ref_norm):
    """Compare spectral norms of two Norm objects for **field**."""
    assert isinstance(test_norm, Norms)
    assert isinstance(ref_norm, Norms)
    return number_of_different_digits(test_norm.spnorms[field],
                                      ref_norm.spnorms[field])


def _compare_gpnorm_for(field, test_norm, ref_norm):
    """Compare gridpoint norms of two Norm objects for **field**."""
    assert isinstance(test_norm, Norms)
    assert isinstance(ref_norm, Norms)
    norms = {}
    for s in ('average', 'minimum', 'maximum'):
        norms[s] = number_of_different_digits(test_norm.gpnorms[field][s],
                                              ref_norm.gpnorms[field][s])
    digit = max(norms.values())
    return digit


def _write_normcomp_for_field(fieldname, digit, out=sys.stdout):
    """Write **fieldname** and its degree of comparison *digit*."""
    fieldname_width = 30
    digits_len = 2
    arrow = ' --> '
    diffdigits = '{:>{width}} last digits differ'
    unable = '??? unable to compare, check manually ???'
    nan = '!!! Found NaN in norms !!!'
    fmt = arrow + diffdigits
    fmtlen = len(diffdigits.format('', width=digits_len))
    if digit is None or digit == 0:
        out.write('{:>{width}}'.format(fieldname, width=fieldname_width) +
                  ' --> {:=<{width}}'.format('', width=fmtlen))
    elif digit == PARSING_ERROR_CODE:
        out.write('{:>{width}}'.format(fieldname, width=fieldname_width) +
                  ' --> {:<{width}}'.format(unable, width=len(unable)))
    elif digit == FOUND_NAN_ERROR_CODE:
        out.write('{:>{width}}'.format(fieldname, width=fieldname_width) +
                  ' --> {:<{width}}'.format(nan, width=len(nan)))
    else:
        out.write('{:>{width}}'.format(fieldname, width=fieldname_width) +
                  fmt.format(str(digit), width=digits_len))
    out.write('\n')


def _write_normcomp(comp_norm, out=sys.stdout):
    assert isinstance(comp_norm, dict)
    for f, d in comp_norm.items():
        _write_normcomp_for_field(f, d, out)
