from unittest.mock import MagicMock, patch
import vortex
from footprints import proxy as fp


@patch("vortex.tools.systems.OSExtended.ssh")
@patch("socket.gethostname")
def test_child_session_setup(mocked_gethostname, mocked_ssh):
    vortex.config.set_config(
        "services", "cluster_names", ["belenos", "taranis"]
    )
    vortex.config.set_config("ecflow", "sshproxy_wait", 12)
    vortex.config.set_config("ecflow", "sshproxy_retries", 4)
    vortex.config.set_config("ecflow", "sshproxy_retrydelay", 2)
    mocked_gethostname.return_value = "belenos191.belenoshpc.meteo.fr"
    s = fp.service(kind="ecflow", clientpath="/path/to/ecflow_client")
    s.env["ECF_HOST"] = "ecfhost"
    s.env["ECF_PORT"] = 28943

    mocked_ssh.return_value.tunnel.return_value.entranceport = 42

    with s.child_session_setup() as setup:
        assert setup
        assert s.env["ECF_HOST"] == "localhost"
        assert s.env["ECF_PORT"] == 42

    mocked_ssh.assert_called_once_with(
        hostname="belenosoper-int",
        mandatory_hostcheck=False,
        maxtries=4,
        triesdelay=2,
    )
    mocked_ssh.return_value.tunnel.assert_called_once_with(
        "ecfhost",
        28943,
        maxwait=12,
    )
