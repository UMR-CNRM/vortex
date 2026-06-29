from unittest.mock import patch

from vortex.tools.systems import Linux34p
from vortex.config import set_config
from vortex.tools.net import DEFAULT_FTP_PORT

import ftserv


SOURCE = "/path/to/data"
DESTINATION = "/path/to/destination"
HOSTNAME = "hendrix.meteo.fr"
LOGNAME = "username"
FTSERV_PATTERNS = "(belenos|taranis|sxcoope)transfert\\d.\\1hpc.meteo.fr|sxcoope1"

def make_system():
    system = Linux34p()
    system.register_ftp_method(
            getfunc=ftserv.ftserv.rawftget,
            putfunc=ftserv.ftserv.rawftput,
            getcond=ftserv.ftserv._use_ftserv_get,
            putcond=ftserv.ftserv._use_ftserv_put,
        )
    return system

@patch("ftserv.ftserv.rawftget")
@patch("vortex.tools.systems.OSExtended.ftget")
def test_smartftget_uses_ftget_when_ftserv_condition_is_false(mocked_ftget, mocked_rawftget):
    # VORTEX_CONFIG["ftserv"]["hostname_patterns"] is empty.
    # One expects:
    #   - FtServ condition is False;
    #   - rawftget is NOT called;
    #   - ftget is called once.
    
    set_config("ftserv", 
               "hostname_patterns", 
               [],
               )
    
    system = make_system()
    
    system.smartftget(SOURCE, 
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

@patch("ftserv.ftserv.rawftget")
@patch("vortex.tools.systems.OSExtended.ftget")
def test_smartftget_uses_rawftget_when_ftserv_condition_is_true(mocked_ftget, mocked_rawftget):   
    # VORTEX_CONFIG["ftserv"]["hostname_patterns"] contains the list of the
    # authorized machines where FtServ may be used.
    # One expects:
    #   - FtServ condition is True;
    #   - ftget is NOT called;
    #   - rawftget is called once.
    
    system = make_system()
    set_config("ftserv", 
               "hostname_patterns", 
               [FTSERV_PATTERNS],
               )
    
    system.smartftget(SOURCE, 
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


@patch("ftserv.ftserv.rawftput")
@patch("vortex.tools.systems.OSExtended.ftput")
def test_smartftput_uses_ftput_when_ftserv_condition_is_false(mocked_ftput, mocked_rawftput):
    # VORTEX_CONFIG["ftserv"]["hostname_patterns"] is empty.
    # One expects:
    #   - FtServ condition is False;
    #   - rawftput is NOT called
    #   - ftput is called once.
    
    set_config("ftserv", 
               "hostname_patterns", 
               [],
               )

    system = make_system()
    
    system.smartftput(SOURCE, 
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
        cpipeline=None,
        sync=False,
        fmt=None,
        )


@patch("ftserv.ftserv.rawftput")
@patch("vortex.tools.systems.OSExtended.ftput")
def test_smartftput_uses_rawftput_when_ftserv_condition_is_true(mocked_ftput, mocked_rawftput):
    # VORTEX_CONFIG["ftserv"]["hostname_patterns"] contains the list of the
    # authorized machines where FtServ may be used.
    # One expects:
    #   - FtServ condition is True;
    #   - ftput is NOT called;
    #   - rawftput is called once.
    
    set_config("ftserv", 
                "hostname_patterns", 
                [FTSERV_PATTERNS],
                )

    system = make_system()
    
    system.smartftput(SOURCE, 
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
