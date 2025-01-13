"""
Utility classes and function to work with the BDAP database.
"""

#: No automatic export
__all__ = []


class BDAPError(Exception):
    """General BDAP error."""

    pass


class BDAPRequestConfigurationError(BDAPError):
    """Specific Transfer Agent configuration error."""

    pass


class BDAPGetError(BDAPError):
    """Generic BDAP get error."""

    pass


def BDAPrequest_actual_command(command, date, term, query, int_extraenv=False):
    """Build the command able to execute a BDAP request.

    The context, the execution path and the command name are
    provided by the configuration file of the target.

    The resulting command should be executed on a transfer node.

    :param command: name of the BDAP request command to be used
    :param date: the date of the file requested
    :param term: the term of the file requested
    :param query: the query file used for the request
    :param int_extraenv: boolean to know if the integration BDAP is used or not
                         (an additional environment variable has to be exported in this case).
    """

    # Environment variable to specify the date of the file
    context = " ; ".join(
        ["export {}={}".format("dmt_date_pivot".upper(), date.ymdhms)]
    )
    # Extra environment variables (integration BDAP)
    if int_extraenv:
        context = " ; ".join(
            [context]
            + [
                "export {}={}".format(
                    "db_file_bdap".upper(),
                    "/usr/local/sopra/neons_db_bdap.intgr",
                )
            ]
        )
    # Return the command to be launched
    return "{} ; {} {:d} {}".format(context, command, term.hour, query)
