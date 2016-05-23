#!/usr/bin/env python2.7
# encoding: utf-8
'''
Automatically generates an ReST file based on a given configuration file.
'''

from __future__ import print_function

argparse_epilog = '''
The ReST code is contained directly in the configuration files:
  - If a line starts with *#R* or *;R*, it will be treated as pure ReST code
  - A section or a configuration key may commented by inserting a *;R* comment
    specified after the section name (or configuration key definition).
  - A configuration key may be commented out if a *;R* comment is specified
    after the section name.

.. example::

    #R =======
    #R Section
    #R =======
    #R
    [section] ;R The section description
    key1 = value ;R The key1 description

'''

import sys
import os
import re

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

# Automatically set the python path
vortexbase = os.path.dirname(os.path.abspath(__file__)).rstrip('/bin')
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

import footprints as fp
import vortex
from vortex.data import geometries
from vortex.util.config import GenericConfigParser

# Main script logger
logger = fp.loggers.getLogger(__name__)


def default_section_cb(parser, section, comment, ckeys):
    """Generate bits of ReST code for a given section."""
    outstr = ':{}:\n'.format(section)
    outstr += '    *{}*\n\n'.format(comment if comment else 'Not documented yet')
    maxk = max([len(k) for k, v in parser.items(section)])
    for k, v in parser.items(section):
        outstr += '    ``{} = {}``  {}\n\n'.format(k.ljust(maxk), v,
                                                   '(`{}`)'.format(ckeys[k]) if ckeys.get(k, None) else '')
    outstr += '    |'
    return outstr


def geometry_easydump(parser, section, comment, ckeys):
    """Generate bits of ReST code for a given geometry."""
    geo = geometries.get(tag=section)
    outstr = '**{}**: `{}`\n    {}\n'.format(section, geo.doc_export(), geo.info)
    return outstr


class RstConfigFileParser(object):

    _RST_COMMENT_LINE = re.compile(r'^[#;]R ?(.*)$')
    _RST_SECTION = re.compile(r's*\[(.*)\]\s+')
    _RST_CONFKEY = re.compile(r's*([-_\w]+)\s+=')
    _RST_SECTION_COMMENT = re.compile(r'^.*\s+;R (.*)$')

    def __init__(self, conffile, section_cb=default_section_cb):
        """A ReST aware configuration parse.

        :param conffile: path to the configuration file
        :param section_cb: function that will handle the formating of each
            detected section
        """
        self._conffile = conffile
        self._section_cb = section_cb
        self._fp = open(conffile, 'r')
        self._parser = GenericConfigParser(conffile)

    def __del__(self):
        self._fp.close()

    def parse(self):
        """
        Parse the configuration file to find out how ReST instructions and
        configuration sections are interalaced.
        """
        cur_section = None
        sections_comment = dict()
        sections_keys = dict()
        rstfeed = []
        # First, parse the config file as a text file
        self._fp.seek(0)
        for line in self._fp.readlines():
            # Full line comment
            rematch = self._RST_COMMENT_LINE.match(line)
            if rematch:
                rstfeed.append(rematch.group(1))
                logger.info('Found brut RST: {}'.format(rstfeed[-1]))
                continue
            # Section start
            rematch = self._RST_SECTION.match(line)
            if rematch:
                cur_section = rematch.group(1)
                if cur_section == 'DEFAULT':  # We donot want to display DEFAULT
                    cur_section = None
                    continue
                else:
                    rstfeed.append('#R {}'.format(cur_section))
                # Look for a comment
                sections_comment[cur_section] = None
                sections_keys[cur_section] = dict()
                rematch = self._RST_SECTION_COMMENT.match(line)
                if rematch:
                    sections_comment[cur_section] = rematch.group(1)
                logger.info('Found section:{} comment:{}'.format(cur_section,
                                                                 sections_comment[cur_section]))
                continue
            # Keys
            rematch = (cur_section is not None and self._RST_CONFKEY.match(line))
            if rematch:
                cur_key = rematch.group(1)
                sections_keys[cur_section][cur_key] = None
                rematch = self._RST_SECTION_COMMENT.match(line)
                if rematch:
                    sections_keys[cur_section][cur_key] = rematch.group(1)
                logger.info('Found key:{} section:{} comment:{}'.format(cur_key,
                                                                        cur_section,
                                                                        sections_keys[cur_section][cur_key]))
                continue
        # The build the ReST for the sections
        rstdoc = []
        for element in rstfeed:
            rematch = self._RST_COMMENT_LINE.match(element)
            if rematch:  # We have to expand the section
                cur_section = rematch.group(1)
                logger.debug('Generating ReST for section:{}'.format(cur_section))
                rstdoc.append(self._section_cb(self._parser, cur_section,
                                               sections_comment[cur_section],
                                               sections_keys[cur_section]))
            else:
                rstdoc.append(element)
        return '\n'.join(rstdoc)


def default_rst(infile, outfile, verbose=0):
    """Default parser."""
    rstparse = RstConfigFileParser(infile)
    with open(outfile, 'w') as outfh:
        outfh.write(rstparse.parse())
        logger.debug('Resulting ReST written in: {}'.format(outfile))


def geometry_rst(outfile, verbose=0):
    """Handle the special case of geometries."""
    t = vortex.ticket()
    sh = t.sh
    # Find out where is the default geometry file
    geofile = sh.path.join(t.glove.siteconf, 'geometries.ini')
    logger.info('Processing the following geometry file: {}'.format(geofile))
    # The geometries are reload: it discards changes made in a personal config file
    geometries.load(inifile=geofile, refresh=True, verbose=verbose > 0)
    logger.debug('The default geometry file was reloaded')
    # We are now parsing the ini file manually to find RST code
    rstparse = RstConfigFileParser(geofile, section_cb=geometry_easydump)
    with open(outfile, 'w') as outfh:
        outfh.write(rstparse.parse())
        logger.debug('Resulting ReST written in: {}'.format(outfile))


def main():
    '''Process command line options.'''

    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc

    # Setup the argument parser
    parser = ArgumentParser(description=program_desc, epilog=argparse_epilog,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s].")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--geometry", dest="geometry", action="store_true",
                       help="Generates the documentation for the geometries.")
    group.add_argument("--default", dest="default", action="store",
                       help="Generates the documentation for any config file (default formating).")
    parser.add_argument("output_file", action="store",
                        help="The path to the output file.")
    args = parser.parse_args()

    # Setup logger verbosity
    if args.verbose is None:
        (loglevel_main, loglevel_fp) = ('WARNING', 'WARNING')
    elif args.verbose == 1:
        (loglevel_main, loglevel_fp) = ('INFO', 'INFO')
    elif args.verbose == 2:
        (loglevel_main, loglevel_fp) = ('DEBUG', 'INFO')
    else:
        (loglevel_main, loglevel_fp) = ('DEBUG', 'DEBUG')
    logger.setLevel(loglevel_main)
    vortex.logger.setLevel(loglevel_main)
    fp.logger.setLevel(loglevel_fp)

    if args.geometry:
        geometry_rst(args.output_file, verbose=args.verbose)
    if args.default:
        default_rst(args.default, args.output_file, verbose=args.verbose)

if __name__ == "__main__":
    sys.exit(main())