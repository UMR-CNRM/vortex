#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Generate index.rst files for a given package's documentation.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

from argparse import ArgumentParser
import importlib
import io
import os
import re
import string
import sys

# Automatically set the python path
vortexbase = re.sub('{0:}project{0:}bin$'.format(os.path.sep), '',
                    os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

from bronx.fancies import loggers

# Main script logger
logger = loggers.getLogger(__name__)

_DOC_TEMPLATE = os.path.join(vortexbase, 'project', 'templates',
                             'doc_package_index.tpl')

_DOCEXT = '.rst'
_INDEX = 'index' + _DOCEXT
_TOCINDENT = 3


class RstIndexEntry(object):
    """Holds all the necessary data to build an index file."""

    def __init__(self, packagedir, fileslist, dirslist, mainpack, maxdepth):
        """
        :param str packagedir: relative path to the package represented by this object
        :param list fileslist: global list of .rst files
        :param list dirslist: global list of directories
        :param str mainpack: name of the main package (i.e. vortex, footprints, ...)
        :param int maxdepth: maximum depth in the main package
        """
        self.packagedir = packagedir
        self.my_doc = None
        self.mod_doc = list()
        self.pac_doc = list()
        self.tocdepth = 0
        self._mainpack = mainpack
        self._fillup(fileslist, dirslist, maxdepth)

    @property
    def packname(self):
        """Current package name."""
        return ((self.packagedir and os.path.basename(self.packagedir)) or
                self._mainpack)

    @property
    def packindex(self):
        """Path to the current's package index file."""
        return os.path.join(self.packagedir, _INDEX)

    @property
    def my_module(self):
        """Python represention of the current's module."""
        return (self._f2module(self.my_doc, trim=True)
                if self.my_doc is not None else None)

    @property
    def mod_module(self):
        """Python represention of the children modules."""
        return [self._f2module(s) for s in self.mod_doc]

    @property
    def pac_module(self):
        """Python represention of the children packages."""
        return [self._f2module(s, trim=True) for s in self.pac_doc]

    @property
    def my_doclink(self):
        return (os.path.basename(self.my_doc)[:-len(_DOCEXT)]
                if self.my_doc is not None else '')

    @property
    def mod_doclink(self):
        return [os.path.basename(s)[:-len(_DOCEXT)]
                for s in self.mod_doc]

    @property
    def pac_doclink(self):
        return [os.path.join(os.path.basename(os.path.dirname(s)),
                             os.path.basename(s)[:-len(_DOCEXT)])
                for s in self.pac_doc]

    def redo(self):
        """Do I need to rebuild the indexes (based on the files mtime)."""
        logger.debug('Processing redo for: %s.', self.packindex)
        if not os.path.exists(self.packindex):
            logger.debug("%s not found, let's go.", self.packindex)
            return True
        else:
            mytime = os.path.getmtime(self.packindex)
            # The package directory itself
            deptimes = [os.path.getmtime(self.packagedir if self.packagedir else './'), ]
            # My own's python code (the documentation may have been altered)
            try:
                with loggers.contextboundGlobalLevel('error'):
                    m = importlib.import_module(self.my_module)
            except ImportError:
                logger.warning("%s does not exist, that's weird.", self.my_module)
            else:
                deptimes.append(os.path.getmtime(m.__file__))
            # Sub-packages indexes changes could be a cause for re-indexing
            for subidx in self.pac_doc:
                if not os.path.exists(subidx):
                    logger.warning("%s does not exist, that's weird.", subidx)
                else:
                    deptimes.append(os.path.getmtime(subidx))
            # Sub-modules changes could be a cause for re-indexing
            for submod in self.mod_doc:
                deptimes.append(os.path.getmtime(submod))
            logger.debug('Max of dependency times: %s.', str(max(deptimes)))
            logger.debug('My time is: %s. (redo=%s)', str(mytime), str(max(deptimes) > mytime))
            return max(deptimes) > mytime

    def build_rst(self, versionid):
        """Build the index file."""
        try:
            with loggers.contextboundGlobalLevel('error'):
                m = importlib.import_module(self.my_module)
        except ImportError:
            logger.warning("%s does not exist, that's weird.", self.my_module)
            index_t = "No Python module could be found for {:s}".format(self.my_module)
        else:
            with loggers.contextboundGlobalLevel('error'):
                m = importlib.import_module(self.my_module)
            if hasattr(m, '__tocinfoline__'):
                index_t = m.__tocinfoline__
            elif hasattr(m, '__doc__'):
                index_t = m.__doc__.lstrip("\n").split("\n")[0]
            else:
                index_t = "{:s} - TODO module index infoline".format(self.my_module)
        index_t = index_t.rstrip('.')
        logger.info('{0._mainpack:s}: Creating {0.packindex:s} (header: {1:s})'.
                    format(self, index_t))
        with io.open(self.packindex, 'w', encoding='utf-8') as fhidx:
            fhidx.write(self._process_template(
                packdoc=index_t,
                packdoc_sep=('=' * len(index_t)),
                version_id=versionid,
                depth=self.tocdepth,
                me=self.my_doclink,
                module=self.my_module,
                modules=('\n' + ' ' * _TOCINDENT).join(self.mod_doclink),
                packages=('\n' + ' ' * _TOCINDENT).join(self.pac_doclink), )
            )

    @staticmethod
    def _process_template(**subdict):
        with io.open(_DOC_TEMPLATE, 'r', encoding='utf-8') as fhd:
                tplobj = fhd.read()
        tplobj = string.Template(tplobj)
        return tplobj.substitute(subdict)

    def _fillup(self, fileslist, dirslist, maxdepth):
        """Parse the file and directory list to initialise this object."""
        tmpdepth = rst_depth(self.packagedir)
        self.tocdepth = maxdepth - tmpdepth
        for f in [f for f in fileslist
                  if (rst_depth(f) == tmpdepth + 1 and
                      f.startswith(self.packagedir) and
                      f.endswith(_DOCEXT) and
                      not f.endswith(_INDEX))]:
            if (f == self.packname + _DOCEXT or
                    f.endswith(os.path.sep + self.packname + _DOCEXT)):
                self.my_doc = f
            else:
                self.mod_doc.append(f)
        for d in [d for d in dirslist
                  if (rst_depth(d) == tmpdepth + 1 and
                      d.startswith(self.packagedir))]:
            self.pac_doc.append(os.path.join(d, _INDEX))
        self.mod_doc.sort()
        self.pac_doc.sort()
        logger.debug('Detected index: %s (self doc: %s).', self.packindex, self.my_doc)
        logger.debug('Detected sub-modules: %s.', str(self.mod_module))
        logger.debug('Detected sub-packages: %s.', str(self.pac_module))

    def _f2module(self, fname, trim=False):
        """Find a Python module name based on the rst file path (**fname**)."""
        if trim:
            fname = os.path.split(fname)[0]
        striped_fname = fname[:-len(_DOCEXT)] if fname.rfind(_DOCEXT) >= 0 else fname
        return (self._mainpack + '.' +
                striped_fname.replace(os.path.sep, '.')).rstrip('.')


def path_cleaner(ppath):
    """Clean the ppath argument and jump to the appropriate directory."""
    cleaned = ppath.rstrip('/')
    if cleaned[0] == '/':
        actual_path = cleaned
    else:
        curpwd = os.getcwd()
        actual_path = os.path.normpath(os.path.join(curpwd, cleaned))
    actual_packname = os.path.basename(actual_path)

    os.chdir(actual_path)

    return actual_packname


def rst_depth(path):
    """Compute the path depth."""
    return (path and (path.count(os.path.sep) + 1)) or 0


def rst_finder(mainpack):
    """Find all rst files for a given package."""
    allfiles = []
    rstfiles = []
    cleanlist = []
    for root, u_dirs, filenames in os.walk('.'):  # @UnusedVariable
        allfiles.extend([os.path.join(root, f) for f in filenames])
    for a_file in allfiles:
        _, fext = os.path.splitext(a_file)
        if fext == _DOCEXT:
            if os.path.basename(a_file) != _INDEX:
                rstfiles.append(a_file[2:])
            else:
                cleanlist.append(a_file)

    rstdepth = max([0] + [rst_depth(f) for f in rstfiles])
    dirslist = set([os.path.dirname(f) for f in rstfiles])
    rstdirs = [RstIndexEntry(d, rstfiles, dirslist, mainpack, rstdepth) for d in dirslist]
    rstdirs.sort(key=lambda x: x.tocdepth)

    return rstdirs, cleanlist


def clean_indexes(cleanlist):
    """Remove all the index files from a given package documentation."""
    logger.info("The following files are removed: %s", str(cleanlist))
    for f in cleanlist:
        os.unlink(f)


def main():
    """Process command line options."""
    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc

    # Setup the argument parser
    parser = ArgumentParser(description=program_desc)
    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="Set verbosity flag.")
    parser.add_argument("--versionid", action="store", default='version',
                        help="RST's version_id key (default: %(default)s).")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--clean", action="store_true",
                       help="Remove all index files.")
    group.add_argument("--force", action="store_true",
                       help="Force a rebuild of all indexes.")
    parser.add_argument("ppath", action='store',
                        help="Path to the package's documentation")
    args = parser.parse_args()

    # Setup logger verbosity
    if args.verbose is None:
        loglevel_main = 'WARNING'
    elif args.verbose == 1:
        loglevel_main = 'INFO'
    else:
        loglevel_main = 'DEBUG'
    logger.setLevel(loglevel_main)

    actual_packname = path_cleaner(args.ppath)
    logger.info("Working on: %s", actual_packname)

    rstdirs, rstfiles = rst_finder(actual_packname)

    if args.clean:
        logger.debug("Now cleaning ReST %s files.", _INDEX)
        clean_indexes(rstfiles)
        return

    if args.force:
        logger.info("Forcing all index re-generation.")
    else:
        logger.debug("Generating index files whenever needed.")

    for d in rstdirs:
        if args.force or d.redo():
            d.build_rst(args.versionid)


if __name__ == "__main__":
    main()
