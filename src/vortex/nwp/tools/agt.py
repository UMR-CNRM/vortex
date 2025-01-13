"""
TODO: Module documentation.
"""

import collections


class AgtConfigurationError(Exception):
    """Specific Transfer Agent configuration error."""

    pass


def agt_volatile_path(sh):
    """Prefix path to use for the Transfer Agent to consider a file as being "volatile"
    and hard-linking to it instead of expecting it to be present "later".
    """
    config = sh.default_target.config
    if not config.has_section("agt"):
        fmt = 'Missing section "agt" in configuration file\n"{}"'
        raise AgtConfigurationError(fmt.format(config.file))
    return config.get("agt", "agt_volatile")


def agt_actual_command(sh, binary_name, args, extraenv=None):
    """Build the command able to execute a Transfer Agent binary.

    The context, the execution path and the command name are
    provided by the configuration file of the target.

    The resulting command should be executed on a transfer node.

    :param sh: The vortex shell that will be used
    :param binary_name: Key in the configuration file that holds the binary name
    :param args: Argument to the AGT binary
    :param extraenv: Additional environment variables to export (dictionary)
    """
    config = sh.default_target.config
    if not config.has_section("agt"):
        fmt = 'Missing section "agt" in configuration file\n"{}"'
        raise AgtConfigurationError(fmt.format(config.file))

    agt_path = sh.default_target.get("agt_path", default=None)
    agt_bin = sh.default_target.get(binary_name, default=None)
    if not all([agt_path, agt_bin]):
        fmt = 'Missing key "agt_path" or "{}" in configuration file\n"{}"'
        raise AgtConfigurationError(fmt.format(binary_name, config.file))
    cfgkeys = [
        "HOME_SOPRA",
        "LD_LIBRARY_PATH",
        "base_transfert_agent",
        "DIAP_AGENT_NUMPROG_AGENT",
    ]
    context = " ; ".join(
        ["export {}={}".format(key, config.get("agt", key)) for key in cfgkeys]
    )
    if extraenv is not None and isinstance(extraenv, collections.abc.Mapping):
        context = " ; ".join(
            [
                context,
            ]
            + [
                "export {}={}".format(key.upper(), value)
                for (key, value) in extraenv.items()
            ]
        )
    return "{} ; {} {}".format(context, sh.path.join(agt_path, agt_bin), args)
