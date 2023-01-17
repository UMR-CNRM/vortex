# -*- coding: utf-8 -*-

"""
TODO module documentation.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import six

from bronx.fancies import loggers

logger = loggers.getLogger(__name__)


def tramsmet_file(filename, filename_transmet, blocksize=67108864):
    """Add the original file into the 'filename_transmet'.

    :param str filename: original file name
    :param str filename_transmet: transmet file name
    :param int blocksize: the blocksize for I/O operations
    """
    with open(filename_transmet, 'ab') as f_header:
        f_header.write(b'\n\n')
        with open(filename, 'rb') as f:
            while True:
                datablock = f.read(blocksize)
                if not datablock:
                    break
                f_header.write(datablock)


def ttaaii_actual_command(sh, transmet_cmd, transmet_dict, scriptdir):
    """Complete command line that runs 'entete_fichier_transmet'.

    :param ~vortex.tools.systems.OSExtended sh: The vortex shell that will be used
    :param str transmet_cmd: Key in the configuration file that holds the script name
    :param dict transmet_dict: variables to export to dictionary
    :param str scriptdir: Key in the configuration file that holds the script path directory
    :return: command line
    :rtype: str
    """
    options = ''
    for k, w in six.iteritems(transmet_dict):
        options += '{}={} '.format(k, w)
    options += 'FICHIER_ENTETE=entete'
    scriptdir = sh.default_target.get(scriptdir, default=None)
    transmet_cmd = sh.default_target.get(transmet_cmd, default=None)
    if scriptdir is None or transmet_cmd is None:
        raise ValueError('scriptdir and transmet_cmd must be available in the configuration file. ' +
                         '(got {!s} and {!s})'.format(scriptdir, transmet_cmd))
    return 'export {}; {}'.format(options, sh.path.join(scriptdir, transmet_cmd))


def get_ttaaii_transmet_sh(sh, transmet_cmd, transmet_dict, filename, scriptdir, header_infile):
    """Create a file with transmet header and returns the filename used for routing.

    :param ~vortex.tools.systems.OSExtended sh: The vortex shell that will be used
    :param str transmet_cmd: Key in the configuration file that holds the script name
    :param dict transmet_dict: variables used to create transmet header
    :param str filename: initial filename
    :param str scriptdir: script path directory
    :param bool header_infile: if True, add header in initial file before routing
    :return: 'transmet' filename
    :rtype: str
    """
    cmd = ttaaii_actual_command(sh, transmet_cmd, transmet_dict, scriptdir)
    filename_ttaaii = sh.spawn(cmd, shell=True, output=True)[0]
    filename_ttaaii = sh.path.join(sh.path.dirname(filename), filename_ttaaii)
    if header_infile:
        sh.rename('entete', filename_ttaaii)
        tramsmet_file(filename, filename_ttaaii)
    else:
        sh.cp(filename, filename_ttaaii, intent='in')
    return filename_ttaaii
