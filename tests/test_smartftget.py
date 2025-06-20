from unittest.mock import patch

from vortex.tools.systems import Linux34p
from vortex.config import set_config
from vortex.tools.net import DEFAULT_FTP_PORT

SOURCE = "/path/to/data"
DESTINATION = "/path/to/destination"
HOSTNAME = "hendrix.meteo.fr"


@patch("vortex.tools.systems.OSExtended.ftserv_get")
def test_use_ftserv(mocked_ftserv_get):
    system = Linux34p(
        ftserv=None, hostname="belenostransfert3.belenoshpc.meteo.fr"
    )

    set_config(
        "ftserv",
        "hostname_patterns",
        ["(belenos|taranis)transfert\\d.\\1hpc.meteo.fr"],
    )

    system.smartftget(
        source=SOURCE,
        destination=DESTINATION,
        hostname=HOSTNAME,
    )
    mocked_ftserv_get.assert_called_once_with(
        SOURCE,
        DESTINATION,
        HOSTNAME,
        None,
        port=None,
    )


@patch("vortex.tools.systems.OSExtended.ftget")
def test_no_ftserv(mocked_ftget):
    system = Linux34p(ftserv=None, hostname="my_hostname")

    set_config(
        "ftserv",
        "hostname_patterns",
        ["(belenos|taranis)transfert\\d.\\1hpc.meteo.fr"],
    )

    system.smartftget(
        source=SOURCE,
        destination=DESTINATION,
        hostname=HOSTNAME,
    )
    mocked_ftget.assert_called_once_with(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=None,
        port=DEFAULT_FTP_PORT,
        cpipeline=None,
        fmt=None,
    )


@patch("vortex.tools.systems.OSExtended.ftserv_get")
def test_force_ftserv(mocked_ftserv_get):
    system = Linux34p(
        ftserv=True, hostname="belenostransfert3.belenoshpc.meteo.fr"
    )

    system.smartftget(
        source=SOURCE,
        destination=DESTINATION,
        hostname=HOSTNAME,
    )
    mocked_ftserv_get.assert_called_once_with(
        SOURCE,
        DESTINATION,
        HOSTNAME,
        None,
        port=None,
    )
