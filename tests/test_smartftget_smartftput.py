from unittest.mock import Mock, patch

from vortex.tools.systems import Linux34p
from vortex.tools.net import DEFAULT_FTP_PORT

import vortex
from vortex.tools.lfi import use_in_shell

SOURCE = "/path/to/data"
DESTINATION = "/path/to/destination"
HOSTNAME = "hendrix.meteo.fr"
LOGNAME = "username"


@patch("vortex.tools.systems.OSExtended.ftget")
def test_smartftget_uses_default_method(mocked_ftget):
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


@patch("vortex.tools.systems.OSExtended.ftput")
def test_smartftput_uses_default_method(mocked_ftput):
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


@patch("vortex.tools.systems.OSExtended.ftget")
def test_smartftget_uses_new_method_when_getcond_is_true(mocked_ftget):
    mocked_other_ftget = Mock()
    mocked_other_ftput = Mock()
    mocked_other_ftgetbatch = Mock()

    system = Linux34p()
    system.register_ftp_method(
        getfunc=mocked_other_ftget,
        putfunc=mocked_other_ftput,
        getfunc_batch=mocked_other_ftgetbatch,
        getcond=lambda cpipeline=None: True,
        putcond=lambda cpipeline=None: True,
        getcond_batch=lambda cpipeline=None: True,
    )
    system.smartftget(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
    )

    mocked_ftget.assert_not_called()

    mocked_other_ftget.assert_called_once_with(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
        fmt=None,
    )


@patch("vortex.tools.systems.OSExtended.ftput")
def test_smartftput_uses_new_method_when_putcond_is_true(mocked_ftput):
    mocked_other_ftget = Mock()
    mocked_other_ftput = Mock()
    mocked_other_ftgetbatch = Mock()

    system = Linux34p()
    system.register_ftp_method(
        getfunc=mocked_other_ftget,
        putfunc=mocked_other_ftput,
        getfunc_batch=mocked_other_ftgetbatch,
        getcond=lambda cpipeline=None: True,
        putcond=lambda cpipeline=None: True,
        getcond_batch=lambda cpipeline=None: True,
    )

    system.smartftput(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
    )

    mocked_ftput.assert_not_called()

    mocked_other_ftput.assert_called_once_with(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
        fmt=None,
        cpipeline=None,
        sync=False,
    )


@patch("vortex.tools.systems.OSExtended.ftget")
def test_smartftget_fallback_to_default_method_when_getcond_is_false(mocked_ftget):
    mocked_other_ftget = Mock()
    mocked_other_ftput = Mock()
    mocked_other_ftgetbatch = Mock()

    system = Linux34p()
    system.register_ftp_method(
        getfunc=mocked_other_ftget,
        putfunc=mocked_other_ftput,
        getfunc_batch=mocked_other_ftgetbatch,
        getcond=lambda cpipeline=None: False,
        putcond=lambda cpipeline=None: False,
        getcond_batch=lambda cpipeline=None: True,
    )

    system.smartftget(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
    )

    mocked_other_ftget.assert_not_called()

    mocked_ftget.assert_called_once_with(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
        fmt=None,
    )


@patch("vortex.tools.systems.OSExtended.ftput")
def test_smartftput_fallback_to_default_method_when_putcond_is_false(mocked_ftput):
    mocked_other_ftget = Mock()
    mocked_other_ftput = Mock()
    mocked_other_ftgetbatch = Mock()

    system = Linux34p()
    system.register_ftp_method(
        getfunc=mocked_other_ftget,
        putfunc=mocked_other_ftput,
        getfunc_batch=mocked_other_ftgetbatch,
        getcond=lambda cpipeline=None: False,
        putcond=lambda cpipeline=None: False,
        getcond_batch=lambda cpipeline=None: True,
    )

    system.smartftput(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
    )

    mocked_other_ftput.assert_not_called()

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


# fa_ftput is called when fmt='fa'
@patch("vortex.tools.lfi.LFI_Tool_Raw.fa_ftput")
def test_smartftput_uses_fa_ftput(mocked_fa_ftput):
    ticket = vortex.ticket()

    # Extend the shell with the LFI interface.
    use_in_shell(sh=ticket.sh, kind="lfi")

    ticket.sh.smartftput(
        SOURCE,
        DESTINATION,
        hostname=HOSTNAME,
        logname=LOGNAME,
        port=DEFAULT_FTP_PORT,
        fmt="fa", # trigger the call to fa_ftput
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
