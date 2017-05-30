#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import

import collections


class AgtConfigurationError(Exception):
    """Specific Transfer Agent configuration error."""
    pass


def agt_actual_command(sh, binary_name, args, extraenv=None):
    """Build the command able to execute a Transfer Agent binary.

    The context, the execution path and the command name are
    provided by the configuration file of the target.

    The resulting command should be executed on a transfer node.

    :param sh: The vortex shell that will be used
    :param binary_name: Key in the configuration file that holds the ninary name
    :param args: Argument to the AGT binary
    :param extraenv: Additional environnement variables to export (dictionnary)
    """
    config = sh.default_target.config
    if not config.has_section('agt'):
        fmt = 'Missing section "agt" in configuration file\n"{}"'
        raise AgtConfigurationError(fmt.format(config.file))

    agt_path = sh.default_target.get('agt_path', default=None)
    agt_bin = sh.default_target.get(binary_name, default=None)
    if not all([agt_path, agt_bin]):
        fmt = 'Missing key "agt_path" or "{}" in configuration file\n"{}"'
        raise AgtConfigurationError(fmt.format(binary_name, config.file))
    cfgkeys = ['HOME_SOPRA', 'LD_LIBRARY_PATH',
               'base_transfert_agent', 'DIAP_AGENT_NUMPROG_AGENT']
    context = ' ; '.join(["export {}={}".format(key, config.get('agt', key))
                          for key in cfgkeys])
    if extraenv is not None and isinstance(extraenv, collections.Mapping):
        context = ' ; '.join([context, ] +
                             ["export {}={}".format(key.upper(), value)
                              for (key, value) in extraenv.iteritems()])
    return '{} ; {} {}'.format(context, sh.path.join(agt_path, agt_bin), args)
