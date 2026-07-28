from unittest.mock import Mock, patch

from vortex.tools.systems import Linux34p
from vortex.tools.net import DEFAULT_FTP_PORT

import vortex
from vortex.tools.lfi import use_in_shell

import pytest


SOURCE = "/path/to/data"
DESTINATION = "/path/to/destination"
HOSTNAME = "hendrix.meteo.fr"
LOGNAME = "username"


# smartftget -> default method.
@patch("vortex.tools.systems.OSExtended.ftget")
def test_smartftget(mocked_ftget):
    system = Linux34p()

    system.smartftget(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
    )

    mocked_ftget.assert_called_once_with(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
        fmt=None,
    )


# smartftput -> default method.
@patch("vortex.tools.systems.OSExtended.ftput")
def test_smartftput(mocked_ftput):
    system = Linux34p()

    system.smartftput(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
    )

    mocked_ftput.assert_called_once_with(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
        cpipeline=None,
        fmt=None,
        sync=False,
    )


# smartftget -> new method if getcond=True.
@patch("vortex.tools.systems.OSExtended.ftget")
def test_smartftget_uses_new_method_when_getcond_is_true(mocked_ftget):
    mocked_rawftget = Mock()
    mocked_rawftput = Mock()

    system = Linux34p()
    system.register_ftp_method(
        mocked_rawftget,
        mocked_rawftput,
        lambda cpipeline=None: True,
        lambda cpipeline=None, source=SOURCE: True,
    )
    system.smartftget(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
    )

    mocked_ftget.assert_not_called()

    mocked_rawftget.assert_called_once_with(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
        fmt=None,
    )


# smartftput -> new method if putcond=True.
@patch("vortex.tools.systems.OSExtended.ftput")
def test_smartftput_uses_new_method_when_putcond_is_true(mocked_ftput):
    mocked_rawftget = Mock()
    mocked_rawftput = Mock()

    system = Linux34p()
    system.register_ftp_method(
        mocked_rawftget,
        mocked_rawftput,
        lambda cpipeline=None: True,
        lambda cpipeline=None, source=SOURCE: True,
    )

    system.smartftput(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
    )

    mocked_ftput.assert_not_called()

    mocked_rawftput.assert_called_once_with(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
        fmt=None,
        cpipeline=None,
        sync=False,
    )


# smartftget -> fallback to the default method if getcond=False.
@patch("vortex.tools.systems.OSExtended.ftget")
def test_smartftget_uses_default_method_when_getcond_is_false(mocked_ftget):
    mocked_rawftget = Mock()
    mocked_rawftput = Mock()

    system = Linux34p()
    system.register_ftp_method(
        mocked_rawftget,
        mocked_rawftput,
        lambda cpipeline=None: False,
        lambda cpipeline=None, source=SOURCE: False,
    )

    system.smartftget(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
    )

    mocked_rawftget.assert_not_called()

    mocked_ftget.assert_called_once_with(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
        fmt=None,
    )


# smartftput -> fallback to the default method if putcond=False.
@patch("vortex.tools.systems.OSExtended.ftput")
def test_smartftput_uses_default_method_when_putcond_is_false(mocked_ftput):
    mocked_rawftget = Mock()
    mocked_rawftput = Mock()

    system = Linux34p()
    system.register_ftp_method(
        mocked_rawftget,
        mocked_rawftput,
        lambda cpipeline=None: False,
        lambda cpipeline=None, source=SOURCE: False,
    )

    system.smartftput(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
    )

    mocked_rawftput.assert_not_called()

    mocked_ftput.assert_called_once_with(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
        fmt=None,
        cpipeline=None,
        sync=False,
    )


# With fmt="fa", @fmtshcmd dispatches the ftput call to fa_ftput.
@patch("vortex.tools.lfi.LFI_Tool_Raw.fa_ftput")
def test_smartftput_fa(mocked_fa_ftput):
    ticket = vortex.ticket()

    # Extend the shell with the LFI interface.
    use_in_shell(sh=ticket.sh, kind="lfi")

    ticket.sh.smartftput(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
        fmt="fa",  # triggers the call to fa_ftput
    )

    mocked_fa_ftput.assert_called_once_with(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
        cpipeline=None,
        sync=False,
    )


# Check that XLFI files are detected by fa_ftput.
def test_smartftput_fa_xlfi(tmp_path):
    source = tmp_path / "source.fa"
    source.write_bytes(b"LFI_ALTM")
    source = str(source)

    ticket = vortex.ticket()

    use_in_shell(sh=ticket.sh, kind="lfi")

    assert ticket.sh.is_xlfi(source)

    cpipeline = object()  # not None, to stop before the FTP transfer.

    with pytest.raises(
        OSError,
        match="It's not allowed to compress xlfi files.",
    ):
        ticket.sh.smartftput(
            source,
            DESTINATION,
            hostname=HOSTNAME,
            logname=LOGNAME,
            port=DEFAULT_FTP_PORT,
            fmt="fa",
            cpipeline=cpipeline,
        )
