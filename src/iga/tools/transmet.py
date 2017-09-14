#!/usr/bin/env python
# -*- coding: utf-8 -*-

import footprints
logger = footprints.loggers.getLogger(__name__)


def tramsmet_file(filename, filename_transmet):
    """"Add the original file into the 'filename_transmet'

    :param filename: original file
    :param filename_transmet: transmet file
    """

    with open(filename, 'rb') as f:
        file_init = f.read()
    with open(filename_transmet, 'a') as f_header:
        f_header.write('\n\n')
        f_header.write(file_init)


def ttaaii_actual_command(sh, transmet_cmd, transmet_dict, scriptdir):
    """Complete command line that runs 'entete_fichier_transmet'

    :param sh: The vortex shell that will be used
    :param transmet_cmd: Key in the configuration file that holds the script name
    :param transmet_dict: variables to export to dictionary  (dictionary)
    :param scriptdir: script path directory
    :return: command line
    """

    options = ''
    for k, w in transmet_dict.iteritems():
        options += '{}={} '.format(k,w)
    options += 'FICHIER_ENTETE=entete'
    scriptdir = sh.default_target.get(scriptdir, default=None)
    transmet_cmd = sh.default_target.get(transmet_cmd, default=None)
    return 'export {}; {}'.format(options, sh.path.join(scriptdir, transmet_cmd))


def execute_cmd_sh(sh, cmd):
    """execute shell command

    :param sh: The vortex shell that will be used
    :param cmd: commmand
    :return: result of command
    """

    logger.info('excute command : %s', cmd)
    return sh.spawn(cmd, shell=True, output=True)


def get_ttaaii_transmet_sh(sh, transmet_cmd, transmet_dict, filename, scriptdir):
    """"create a file with transmet header and returns the filename used for routing.

    :param sh: The vortex shell that will be used
    :param transmet_cmd: Key in the configuration file that holds the script name
    :param transmet_dict: variables used to create transmet header (dictionary)
    :param filename: initial filename
    :param scriptdir: script path directory
    :return 'transmet' filename
    """

    cmd = ttaaii_actual_command(sh, transmet_cmd, transmet_dict, scriptdir)
    filename_ttaaii = execute_cmd_sh(sh, cmd)[0]
    filename_ttaaii = str(sh.path.join(sh.path.dirname(filename), filename_ttaaii))
    sh.rename('entete', filename_ttaaii)
    tramsmet_file(filename, filename_ttaaii)
    return filename_ttaaii
