from unittest.mock import patch

import vortex
from vortex.tools.net import Ssh


@patch("socket.gethostname")
def test_ssh_config(mocked_gethostname, tmp_path):
    vortex.config.set_config("ssh", "sshcmd", "mysshcmd")
    vortex.config.set_config(
        "ssh",
        "sshopts",
        {"default": "default_opts", "sotrtm\\d\\d-sidev": "other opts"},
    )

    mocked_gethostname.return_value = "sotrtm35-sidev"

    sshobj = Ssh(vortex.ticket().sh, "myhostname")

    assert sshobj._sshcmd == "mysshcmd"
    assert sshobj._scpcmd == "scp"  # The default
    assert sshobj._sshopts == ["other", "opts"]
    assert sshobj._scpopts == []
