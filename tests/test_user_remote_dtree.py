from unittest.mock import patch

import vortex as vtx

# Vortex storage configuration
vtx.config.set_config(
    section="storage", key="rootdir", value="/path/to/%usr%/vortex"
)
vtx.config.set_config(
    section="storage", key="op_rootdir", value="/path/to/op/tree"
)
vtx.config.set_config(
    section="storage", key="address", value="example.meteo.fr"
)
vtx.config.set_config(section="storage", key="protocol", value="ftp")

# Set a vortex resource description we will reuse throughout
# Note that it does not specify the username argument
FP_DESC = {
    "vapp": "arpege",
    "vconf": "4dvarfr",
    "cutoff": "production",
    "date": "202506160000",
    "term": [2],
    "geometry": "global1798",
    "model": "arpege",
    "block": "forecast",
    "kind": "modelstate",
    "experiment": "exp",
    "local": "local_file_name",
    "namespace": "vortex.archive.fr",
}


@patch("vortex.tools.systems.OSExtended.smartftget")
@patch("vortex.sessions.Ticket.glove")
def test_default_tree(mocked_glove, mocked_smartftget):
    mocked_glove.user = "user"
    mocked_smartftget.return_value = True
    rh = vtx.input(**FP_DESC)[0]
    rh.get()
    mocked_smartftget.assert_called_once_with(
        "/path/to/user/vortex/arpege/4dvarfr/exp/20250616T0000P/forecast/historic.arpege.tl1798-c22+0002:00.fa",
        "local_file_name",
        hostname="example.meteo.fr",
        logname=None,
        fmt="fa",
        cpipeline=None,
    )


@patch("vortex.tools.systems.OSExtended.smartftget")
@patch("vortex.sessions.Ticket.glove")
def test_otheruser_tree(mocked_glove, mocked_smartftget):
    mocked_glove.user = "user"
    mocked_smartftget.return_value = True

    # Add the username argument to the resource (provider) description
    fp = FP_DESC | {"username": "otheruser"}
    rh = vtx.input(**fp)[0]
    rh.get()
    mocked_smartftget.assert_called_once_with(
        # File is fetched from otheruser's tree
        "/path/to/otheruser/vortex/arpege/4dvarfr/exp/20250616T0000P/forecast/historic.arpege.tl1798-c22+0002:00.fa",
        "local_file_name",
        hostname="example.meteo.fr",
        logname=None,
        fmt="fa",
        cpipeline=None,
    )


@patch("vortex.tools.systems.OSExtended.smartftget")
@patch("vortex.sessions.Ticket.glove")
def test_oper_tree(mocked_glove, mocked_smartftget):
    mocked_glove.user = "user"
    mocked_smartftget.return_value = True

    # Still specify username=otheruser but setting experiment to oper
    # special exp overrides behavior.
    fp = FP_DESC | {"username": "otheruser"} | {"experiment": "oper"}
    rh = vtx.input(**fp)[0]
    rh.get()
    mocked_smartftget.assert_called_once_with(
        "/path/to/op/tree/arpege/4dvarfr/oper/2025/06/16/T0000P/forecast/historic.arpege.tl1798-c22+0002:00.fa",
        "local_file_name",
        hostname="example.meteo.fr",
        logname=None,
        fmt="fa",
        cpipeline=None,
    )
