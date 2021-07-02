#!/usr/bin/env python3
# encoding: utf-8
"""
project.bin.coutlines -- count the lines of code in the project

Uses the "cloc.pl" software to compute the number of lines of code in specific
folders of the vortex project
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import argparse
import collections
import xml.etree.ElementTree as ET
import subprocess
import re


ClocResultLineTp = collections.namedtuple('ClocResultLine',
                                          ('blank', 'comment', 'code', 'useful'))


class ClocResultLine(ClocResultLineTp):
    """Just one bit of cloc.pl results"""
    def __new__(self, ldict):
        return ClocResultLineTp.__new__(self, int(ldict['blank']),
                                        int(ldict['comment']),
                                        int(ldict['code']),
                                        int(ldict['comment']) + int(ldict['code']))


class ClocResult():
    """Handle cloc.pl results in XML format."""
    res_head = '{:20s}:  {:>8s}  {:>8s}  {:>8s}  {:>8s}'.format('Language',
                                                                'Blank',
                                                                'Comment',
                                                                'Code',
                                                                'Useful')
    res_fmt = '{:20s}:  {:8d}  {:8d}  {:8d}  {:8d}'

    def __init__(self, xmloutput):
        root = ET.fromstring(re.sub('^\n*', '', xmloutput))
        self.languages = {}
        for lang in [l.attrib for l in root.iter('language')]:
            self.languages[lang['name']] = ClocResultLine(lang)
        for total in [l.attrib for l in root.iter('total')]:
            self.total = ClocResultLine(total)

    def __str__(self):
        out = [self.res_head, ]
        for lang, res in self.languages.iteritems():
            out.append(self.res_fmt.format(lang, *res))
        out.append(self.res_fmt.format('TOTAL', *self.total))
        return '\n'.join(out)


def subdir_analyse(subdir, clocbin, clocdef):
    """Launch cloc.pl on a given list of directories."""
    cmdl = [clocbin,
            '--quiet',
            '--xml',
            '--skip-uniqueness', ]
    if clocdef:
        cmdl.append('--force-lang-def={}'.format(clocdef))
    cmdl.extend(subdir.split(','))
    return ClocResult(subprocess.check_output(cmdl))


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Uses the "cloc.pl" software to compute the number of ' +
                    'lines of code in specific folders of the vortex project',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('subdirs', action='store', nargs='+',
                        help='List of sub-directories to process')
    parser.add_argument('--clocdef', '-d', action='store', type=str,
                        help='Path to a cloc definition file')
    parser.add_argument('--clocpath', '-p', action='store', default='cloc.pl',
                        help='Path to the cloc.pl software')
    args = parser.parse_args()

    for subdir in args.subdirs:
        print('{:-^80s}'.format('Subdirectories: ' + subdir))
        print(subdir_analyse(subdir, args.clocpath, args.clocdef))
