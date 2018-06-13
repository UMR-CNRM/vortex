#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This module contains the generic interface used for ECtrans and ECfs.
"""

from __future__ import print_function, absolute_import, unicode_literals, division


import re
import itertools

import footprints

logger = footprints.loggers.getLogger(__name__)


class ECMWFInterface(object):
    """Generic Python interface at ECMWF."""

    def __init__(self, system, command, command_interface):
        """Initialization function"""
        self._system = system
        self._command = command
        self._command_interface = command_interface

    @property
    def system(self):
        """Return the system object used by the interface"""
        return self._system

    @property
    def command(self):
        """Return the _command attribute"""
        return self._command

    @property
    def command_interface(self):
        """Return True if a command line contains a command name, False else."""
        return self._command_interface

    def actual_command(self, command=None):
        """Return the command header used in the command line"""
        if command is None:
            return self.command
        else:
            return command

    def __call__(self, list_args=list(), dict_args=dict(), list_options=list(), command=None):
        """Construct the command line and run it in the shell"""
        actual_command = self.actual_command(command)
        command_line = self.build_command_line(command=actual_command,
                                               list_args=list_args,
                                               dict_args=dict_args,
                                               list_options=list_options)
        logger.debug("The command line launched is: {}".format(command_line))
        return self.system.spawn(command_line, shell = False, output = False)

    @staticmethod
    def build_command_line(command, list_args, dict_args, list_options):
        """
        Build the command line using the different elements passed to the function.

        :param command: header of the command line
        :param list_args: list of positional arguments
        :param dict_args: list of named options with value(s)
        :param list_options: list of named options without values
        :return: the complete command line
        """
        # Initialize the command line with the header
        command_line = command
        # Add positional arguments
        for arg in list_args:
            command_line = " ".join([command_line, arg])
        # Add named options with value(s)
        for kwarg, value in dict_args.items():
            if isinstance(value, (set, list, tuple)):
                value = " ".join([val for val in value])
            command_line = " ".join([command_line, '-{attr} {val}'.format(attr=kwarg, val=value)])
        # Add named options without value
        for arg in list_options:
            command_line = " ".join([command_line, '-{attr}'.format(attr=arg)])
        return command_line

    def prepare_arguments(self, list_args):
        """
        Read the command line passed to the script and format in order to be readable by the interface

        :param list_args: the list of arguments passed to the script
        :return: the elements needed by the interface:
                - header of the command line
                - positional arguments
                - named options with value(s)
                - named options without value
        """
        # Initialize different elements
        command = None
        args = list()
        kwargs = dict()
        options = list()
        template_kwarg = re.compile(r'^-(?P<attr>(\w*\W*)*)=(?P<value>(\w*\W*)*)$')
        template_arg = re.compile(r'^-(?P<attr>(\w*\W*)*)$')
        # Read the arguments' list
        for arg in itertools.islice(list_args, 1, None):
            # Read and format the different elements
            match_kwarg_template = template_kwarg.match(arg)
            match_arg_template = template_arg.match(arg)
            if match_kwarg_template:
                attr = match_kwarg_template.group('attr')
                value = match_kwarg_template.group('value')
                value = value.split(',')
                if len(value) == 1:
                    value = value[0]
                kwargs[attr] = value
            elif match_arg_template:
                attr = match_arg_template.group('attr')
                options.append(attr)
            else:
                args.append(arg)
        # Get the command name
        if len(args) > 0 and self.command_interface:
            command = args.pop(0)
        return command, args, kwargs, options


class ECfs(ECMWFInterface):
    """Python interface for ECfs"""

    def __init__(self, system):
        super(ECfs, self).__init__(system=system,
                             command="ecfs",
                             command_interface=True)


class ECtrans(ECMWFInterface):
    """Python interface for ECtrans"""

    def __init__(self, system):
        super(ECtrans, self).__init__(system=system,
                                command="ectrans",
                                command_interface=False)
