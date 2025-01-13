"""
Utility classes and function to work with the BDMP database.
"""

#: No automatic export
__all__ = []


class BDMPError(Exception):
    """General BDMP error."""

    pass


class BDMPRequestConfigurationError(BDMPError):
    """Specific Transfer Agent configuration error."""

    pass


class BDMPGetError(BDMPError):
    """Generic BDMP get error."""

    pass


def BDMPrequest_actual_command(command, query, target_bdmp):
    """Build the command able to execute a BDMP request.

    The context, the execution path and the command name are
    provided by the configuration file of the target.

    The resulting command should be executed on a transfer node.

    :param command: name of the BDMP request command to be used
    :param query: the query file used for the request
    :param target_bdmp: string to determine the BDMP used
    """
    # Environment variable used for the request
    extraenv_pwd = "export {} {}".format(
        "pwd_file".upper(), "/usr/local/sopra/neons_pwd"
    )
    if target_bdmp == "OPER":
        extraenv_db = "/usr/local/sopra/neons_db_bdm"
    elif target_bdmp == "INTE":
        extraenv_db = "/usr/local/sopra/neons_db_bdm.archi"
    elif target_bdmp == "ARCH":
        extraenv_db = "/usr/local/sopra/neons_db_bdm.intgr"
    else:
        raise BDMPError
    extraenv_db = "export {} {}".format("db_file_bdm".upper(), extraenv_db)

    # Return the command to be launched
    return "{} ; {} ; {} {}".format(extraenv_pwd, extraenv_db, command, query)
