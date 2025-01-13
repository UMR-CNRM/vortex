"""
Utility classes and function to work with the Mars database.
"""

from bronx.fancies import loggers

from vortex.util.config import GenericConfigParser

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class MarsError(Exception):
    """General Mars error."""

    pass


class MarsConfigurationError(MarsError):
    """Specific Mars configuration error."""

    pass


class MarsGetError(MarsError):
    """Generic Mars get error."""

    pass


def findMarsExtractCommand(sh, inifile=None, command=None):
    actual_command = command
    if actual_command is None:
        actual_inifile = inifile
        if actual_inifile is None:
            actual_command = sh.default_target.get("mars:command", None)
        else:
            actual_config = GenericConfigParser(inifile=actual_inifile)
            if actual_config.has_section("mars") and actual_config.has_option(
                "mars", "command"
            ):
                actual_command = actual_config.get("mars", "command")
        if actual_command is None:
            raise MarsConfigurationError("Could not find a proper command.")
    return actual_command


def callMarsExtract(sh, query_file, command=None, fatal=True):
    """
    Build the command line used to execute the Mars query and launch it.

    :param: sh: the system object used
    :param query_file: The file containing the Mars query.
    :param command: The command to be used to launch the Mars extraction.
    :param fatal: Parameter indicating whether the fail of the request should be fatal or not
    :return: The return code of the Mars extraction.
    """
    command_line = " ".join([command, query_file])
    return sh.spawn(
        [
            command_line,
        ],
        shell=True,
        output=False,
        fatal=fatal,
    )
