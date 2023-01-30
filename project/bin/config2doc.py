#!/usr/bin/env python3
"""
Automatically generates an ReST file based on a given configuration file.
"""

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import importlib
import os
import re
import sys

# Automatically set the python path
vortexbase = re.sub('{0:}project{0:}bin$'.format(os.path.sep), '',
                    os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

from bronx.fancies import loggers
import footprints as fp

import vortex
from vortex.data import geometries
from vortex.util.config import GenericConfigParser

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

# Main script logger
logger = loggers.getLogger(__name__)


def default_section_cb(parser, section, comment, ckeys):
    """Generate bits of ReST code for a given section."""
    outstr = ':{}: *{}*\n\n'.format(section,
                                    comment if comment else 'Not documented yet')

    maxk = max(max([len(k) for k in parser.options(section)]), 3)
    maxv = max(max([len(parser.get(section, k)) for k in parser.options(section)]), 5)
    maxck = max(max([len(ckeys.get(k, None) or '') for k in parser.options(section)]), 8)
    outstr += '    ' + '=' * maxk + ' ' + '=' * maxv + ' ' + '=' * maxck + "\n"
    outstr += '    ' + 'Key'.ljust(maxk) + ' ' + 'Value'.ljust(maxv) + ' ' + 'Comment'.ljust(maxck) + "\n"
    outstr += '    ' + '=' * maxk + ' ' + '=' * maxv + ' ' + '=' * maxck + "\n"

    tablerows = list()
    for k in parser.options(section):
        tablerows.append('    ' + k.ljust(maxk) + ' ' +
                         parser.get(section, k).ljust(maxv) + ' ' +
                         (ckeys.get(k, None) or '').ljust(maxck) + "\n")
    outstr += ('    ' + '-' * maxk + ' ' + '-' * maxv + ' ' + '-' * maxck + "\n").join(tablerows)
    outstr += '    ' + '=' * maxk + ' ' + '=' * maxv + ' ' + '=' * maxck + "\n\n"
    return outstr


def geometry_easydump(parser, section, comment, ckeys):
    """Generate bits of ReST code for a given geometry."""
    geo = geometries.get(tag=section)
    outstr = '**{}**: `{}`\n    {}\n'.format(section, geo.doc_export(), geo.info)
    return outstr


class RstConfigFileParser:
    """Read and Process the configuration file to document."""

    _RST_COMMENT_LINE = re.compile(r'^[#;]R\s+(.*)$')
    _RST_COMMENT_LINEABOVE = re.compile(r'^[#;]Rabove\s+(.*)$')
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
        self._fp = open(conffile, encoding='utf-8')
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
                if cur_section == 'DEFAULT':  # We do not want to display DEFAULT
                    cur_section = None
                    continue
                else:
                    rstfeed.append('#R {}'.format(cur_section))
                cur_key = None
                # Look for a comment
                sections_comment[cur_section] = None
                sections_keys[cur_section] = dict()
                rematch = self._RST_SECTION_COMMENT.match(line)
                if rematch:
                    sections_comment[cur_section] = rematch.group(1)
                else:
                    sections_comment[cur_section] = ''
                logger.info('Found section:{} comment:{}'.format(cur_section,
                                                                 sections_comment[cur_section]))
                continue
            # Keys
            rematch = (cur_section is not None and self._RST_CONFKEY.match(line))
            if rematch:
                cur_key = rematch.group(1).lower()
                sections_keys[cur_section][cur_key] = None
                rematch = self._RST_SECTION_COMMENT.match(line)
                if rematch:
                    sections_keys[cur_section][cur_key] = rematch.group(1)
                else:
                    sections_keys[cur_section][cur_key] = ''
                logger.info('Found key:{} section:{} comment:{}'.format(cur_key,
                                                                        cur_section,
                                                                        sections_keys[cur_section][cur_key]))
                continue
            # Section's comments
            if cur_section and cur_key is None:
                rematch = self._RST_COMMENT_LINEABOVE.match(line)
                if rematch:
                    sections_comment[cur_section] += (('\n' if sections_comment[cur_section] else '') +
                                                      rematch.group(1))
                    continue
            # Key's comments
            if cur_section and cur_key:
                rematch = self._RST_COMMENT_LINEABOVE.match(line)
                if rematch:
                    sections_keys[cur_section][cur_key] += ((' ' if sections_keys[cur_section][cur_key] else '') +
                                                            rematch.group(1))
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
    with open(outfile, 'w', encoding='utf-8') as outfh:
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
    geometries.load(inifile=geofile, refresh=True, verbose=(verbose or 0) > 0)
    logger.debug('The default geometry file was reloaded')
    # We are now parsing the ini file manually to find RST code
    rstparse = RstConfigFileParser(geofile, section_cb=geometry_easydump)
    with open(outfile, 'w', encoding='utf-8') as outfh:
        outfh.write(rstparse.parse())
        logger.debug('Resulting ReST written in: {}'.format(outfile))


def configtable_rst(indata, outfile, verbose=0):
    """Handle the special case of geometries."""
    idata = indata.split(',')
    if len(idata) >= 5:
        importlib.import_module(idata[4])
    fpargs = dict(family=idata[0],
                  kind=idata[1],
                  version=idata[2],
                  language=idata[3] if len(idata) >= 4 else 'en',)
    c_parser = fp.proxy.iniconf(**fpargs)

    def tableitem_easydump(parser, section, comment, ckeys):
        """Generate bits of ReST code for a given tableitem."""
        if ':' in section:
            item = c_parser.get(section.split(':', 1)[0])
            return item.nice_rst()
        else:
            return ''

    # We are now parsing the ini file manually to find RST code
    rstparse = RstConfigFileParser(c_parser.config.file, section_cb=tableitem_easydump)
    with open(outfile, 'w', encoding='utf-8') as outfh:
        outfh.write(rstparse.parse())
        logger.debug('Resulting ReST written in: {}'.format(outfile))


def main():
    """Process command line options."""

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
    group.add_argument("--configtable", dest="configtable", action="store",
                       help=("Generates the documentation for a config table. " +
                             "Must be a coma separated list (family,kind,version,lang,package)"))
    group.add_argument("--default", dest="default", action="store",
                       help=("Generates the documentation for any config file (default formating). " +
                             "The path (relative or absolute) to the config file has to be specified " +
                             "as this argument's option."))
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
    if args.configtable:
        configtable_rst(args.configtable, args.output_file, verbose=args.verbose)
    if args.default:
        default_rst(args.default, args.output_file, verbose=args.verbose)


if __name__ == "__main__":
    main()
