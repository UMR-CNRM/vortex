#!/usr/bin/env python2.7
# encoding: utf-8
"""
Automatically convert notebooks to a set of RST files.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import shutil

argparse_epilog = '''
'''

import collections
import logging
import os
import sys
import re
import tarfile

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

# Try to guess the available tools
try:
    # Starting from IPython 4.0, nbconvert is shipped separately
    import nbconvert
    from nbconvert.exporters import RSTExporter
    export_backend = 'Default'
    tplversion = re.sub(r'^(\d+)\..*$', r'\1', nbconvert.__version__)
    rst_tplfile = 'notebook2sphinx_rst_nbconvert_v{:s}'.format(tplversion)
except ImportError:
    # Old style IPython
    import IPython
    from IPython.nbconvert.exporters import RSTExporter
    export_backend = 'Default'
    tplversion = re.sub(r'^(\d+)\..*$', r'\1', IPython.__version__)
    rst_tplfile = 'notebook2sphinx_rst_ipython_v{:s}'.format(tplversion)

logging.basicConfig()
logger = logging.getLogger(__name__)

_NBOOKS_EXT = ".ipynb"
_DIR_DISCARD = ('.ipynb_checkpoints', )
_INDEX_TOP_HEAD = '''
#################
Notebooks Summary
#################

'''
_INDEX_SUB_HEAD = '''
##############{ti:s}
Subdirectory: {sub:s}
##############{ti:s}

'''
_INDEX_SKEL = 'index_skeleton.rst'
_NBCONVERT_TEMPLATES = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                     '../templates'))


class DefaultPackaging(object):
    """The default class to alter exports."""

    def __call__(self, rst, resources):
        return rst, resources


class DefaultExporter(object):
    """The default class to export notebook's file."""

    def __init__(self, packager, tarname):
        self._packager = packager
        self._tarname = tarname

    def _ipynb_convert(self, a_file):
        """Actually convert the notebook."""
        myname = os.path.splitext(os.path.basename(a_file))[0]
        exporter = RSTExporter(template_path=[_NBCONVERT_TEMPLATES, ],
                               template_file=rst_tplfile)
        rst, resources = exporter.from_filename(a_file,
                                                resources=dict(unique_key=myname))
        logger.debug("%s exported. Name=%s, Outputs=%s",
                     a_file, myname, resources['outputs'].keys())
        return rst, resources

    def _add_automatic_ref(self, rst, myname):
        """Add an automatic reference in the export."""
        return '.. _nbook-{:s}:\n\n{:s}'.format(myname, rst.encode('utf-8'))

    def _add_download(self, rst, a_file):
        """Add a download link in the export."""
        radix = os.path.split(a_file)[0]
        nback = 0
        while radix:
            nback += 1 if radix != '.' else 0
            radix = os.path.split(radix)[0]
        tarpath = '../' * nback + self._tarname
        statement = ('\n' +
                     '.. note::\n' +
                     '   ' +
                     'This page had been generated from a IPython/Jupyter notebook. ' +
                     'You can :download:`download this notebook <{:s}>` individually or '. format(os.path.basename(a_file)) +
                     "get a :download:`tarball <{:s}>` of all the project's notebooks.".format(tarpath) +
                     '\n\n')
        return (statement + rst + statement)

    def _rst_alter(self, rst, resources, a_file):
        """Control the way the exports are altered."""
        myname = resources['unique_key']
        rst = self._add_automatic_ref(rst, myname)
        rst = self._add_download(rst, a_file)
        rst, resources = self._packager(rst, resources)
        return rst, resources

    def _rst_dump(self, rst, resources, outputdir, a_file):
        """Actualy dump the export file to disk."""
        rst_out = os.path.join(outputdir, os.path.splitext(a_file)[0] + '.rst')
        ipnb_out = os.path.join(outputdir, a_file)
        rst_out = os.path.normpath(rst_out)
        rst_dir = os.path.dirname(rst_out)
        if not os.path.exists(rst_dir):
            os.makedirs(rst_dir)
        with open(rst_out, 'w') as rstfh:
            rstfh.write(rst)
        # Also write potential image files
        for additional, rawdata in resources['outputs'].iteritems():
            add_out = os.path.join(rst_dir, additional)
            with open(add_out, 'w') as addfh:
                addfh.write(rawdata)
            logger.debug('Additional file writen: %s', add_out)
        logger.info("written: %s (additions: %s)",
                    rst_out, resources['outputs'].keys())
        # Copy the ipnb file (this will allow to download it)
        shutil.copy(a_file, ipnb_out)

    def __call__(self, outputdir, a_file):
        """Export a given notebook."""
        rst, resources = self._ipynb_convert(a_file)
        rst, resources = self._rst_alter(rst, resources, a_file)
        self._rst_dump(rst, resources, outputdir, a_file)


def _crawl_notebooks():
    """Lists the notebooks."""
    files = list()
    for (dirpath, _, filenames) in os.walk('.'):
        if os.path.basename(dirpath) in _DIR_DISCARD:
            continue
        files.extend([os.path.join(dirpath, f)
                      for f in filenames
                      if os.path.splitext(f)[1] == _NBOOKS_EXT])
    return files


def _crawl_images():
    """Lists the images."""
    files = list()
    for (dirpath, _, filenames) in os.walk('.'):
        if os.path.basename(dirpath) in _DIR_DISCARD:
            continue
        files.extend([os.path.join(dirpath, f)
                      for f in filenames
                      if os.path.splitext(f)[1] in ('.png')])
    return files


def _tar_notebooks(tarname, files):
    """Create a tar file that contains all the notebook files."""
    logger.info("Output tar file is: %s", tarname)
    tarext = os.path.splitext(tarname)[1]
    tarmode_extra = ':' + tarext[1:] if tarext in ('.bz2', '.gz') else ''
    if tarmode_extra:
        logger.debug("Enabling compression on the tar file (%s)", tarmode_extra[1:])
    with open(tarname, 'w') as tarfh:
        tfile = tarfile.open(fileobj=tarfh, mode='w' + tarmode_extra)
        for a_file in files:
            logger.debug("Adding %s to the %s Tar file.", tarname, a_file)
            tfile.add(a_file)
        tfile.close()


def _index_auto_generate(outputdir, files):
    """Generate all the needed index.rst files."""
    # Order the notebooks alphabetically but ignore the case
    toindex = collections.defaultdict(list)
    files.sort(key=lambda f: f.upper())
    for a_file in files:
        radix, rstname = os.path.split(a_file)
        radix = radix.lstrip('./')
        rstname = os.path.splitext(rstname)[0]
        toindex[radix].append(rstname)
        radix_m1, lastdirname = os.path.split(radix)
        if lastdirname != '':
            toindex[radix_m1].append(os.path.join(lastdirname, 'index.rst'))
    toindex = {k: sorted(set(v)) for k, v in toindex.items()}
    toindex_keys = toindex.keys()
    toindex_keys.sort(key=lambda f: f.upper())
    for radix in toindex_keys:
        toc = ('.. toctree::\n   :titlesonly:\n\n' +
               '\n'.join(['   ' + n for n in toindex[radix]]) + '\n\n')
        if os.path.exists(os.path.join(radix, _INDEX_SKEL)):
            with open(os.path.join(radix, _INDEX_SKEL), 'r') as rstfh:
                full = rstfh.read()
        else:
            if radix == '':
                full = _INDEX_TOP_HEAD
            else:
                full = _INDEX_SUB_HEAD.format(sub=radix, ti='#' * len(radix))
        full += toc
        with open(os.path.join(outputdir, radix, 'index.rst'), 'w') as rstfh:
            rstfh.write(full)


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
    parser.add_argument("-o", "--outputdir", dest="outputdir", default='.',
                        action="store",
                        help="output directory [default: %(default)s].")
    parser.add_argument("-t", "--tarname", dest="tarname",
                        default='notebooks.tar.bz2', action="store",
                        help="Tar file name [default: %(default)s].")
    parser.add_argument("-p", "--packaging", dest="packaging",
                        default='Default', action="store",
                        help="Name of the packaging class [default: %(default)s].")
    parser.add_argument("source_directory", action="store",
                        help="source directory to look for notebooks.")
    args = parser.parse_args()

    # Setup logger verbosity
    loglevel_main = {1: 'INFO', 2: 'DEBUG'}.get(args.verbose, 'WARNING')
    logger.setLevel(loglevel_main)

    # Secure the output directory
    abs_outputdir = os.path.abspath(os.path.expanduser(args.outputdir))
    abs_outputdir = os.path.normpath(abs_outputdir)
    if not os.path.isdir(abs_outputdir):
        logger.info("%s does not exists: we are creating it.", abs_outputdir)
        os.makedirs(abs_outputdir)
    logger.debug("Outputdir is: %s", abs_outputdir)

    # Jump to the input directory
    sourcedir = os.path.expanduser(args.source_directory)
    logger.debug("Inputdir is: %s", sourcedir)
    os.chdir(sourcedir)

    # Find out the notebooks list
    files = _crawl_notebooks()
    logger.info("%d notebook found.", len(files))

    images = _crawl_images()
    logger.info("%d images found.", len(images))

    # Create a tar with temp
    _tar_notebooks(os.path.join(abs_outputdir, args.tarname), files + images)

    # Find the packaging class
    packager = globals().get(args.packaging + 'Packaging')()
    # Find the exporter class
    exporter = globals().get(export_backend + 'Exporter')(packager,
                                                          args.tarname)
    # Export the notebooks
    for a_file in files:
        exporter(abs_outputdir, a_file)

    # Copy images
    for a_file in images:
        dest = os.path.join(abs_outputdir, a_file)
        try:
            os.makedirs(os.path.dirname(dest))
        except OSError:
            # directory already exists
            pass
        shutil.copyfile(a_file, dest)

    # Create the indexes (index.rst)
    _index_auto_generate(abs_outputdir, files)


if __name__ == "__main__":
    main()
