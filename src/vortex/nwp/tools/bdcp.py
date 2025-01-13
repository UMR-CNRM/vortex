"""
Utility classes and function to work with the BDCP database.
"""

#: No automatic export
__all__ = []


class BDCPError(Exception):
    """General BDMP error."""

    pass


class BDCPRequestConfigurationError(BDCPError):
    """Specific Transfer Agent configuration error."""

    pass


class BDCPGetError(BDCPError):
    """Generic BDCP get error."""

    pass


def BDCPrequest_actual_command(command, query_file, output_file):
    """Build the command able to execute a BDCP request.

    The context, the execution path and the command name are
    provided by the configuration file of the target.

    The resulting command should be executed on a transfer node.

    :param command: name of the BDMP request command to be used
    :param query_file: the query file used for the request
    :param output_file: the file in which the result will be written
    """

    # Return the command to be launched
    return "{} -D {} -f {}".format(command, query_file, output_file)
