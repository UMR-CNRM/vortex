"""
Hooks for special DAVAI processings.
"""

import json

from bronx.fancies import loggers

from vortex.tools.net import uriparse
from .util import SummariesStack, DavaiException, send_task_to_DAVAI_server

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def take_the_DAVAI_train(t, rh,
                         fatal=True,
                         wagons='__all__'):
    """Usual double put of summaries for DAVAI."""
    if wagons == '__all__':
        wagons = ['ciboulai', 'stack']
    elif isinstance(wagons, str):
        wagons = wagons.split(',')
    # call sub-puts
    if 'ciboulai' in wagons:
        send_to_DAVAI_server(t, rh, fatal=fatal)
    if 'stack' in wagons:
        throw_summary_on_stack(t, rh)


def throw_summary_on_stack(t, rh):
    """
    Put summary on stack (cache directory in which are gathered all summaries).

    :param reload_trolley: if True, reload trolley on-the-fly right afterwards
    """
    stack = SummariesStack(ticket=t,
                           vapp=rh.provider.vapp,
                           vconf=rh.provider.vconf,
                           xpid=rh.provider.experiment)
    stack.throw_on_stack(rh)


def send_to_DAVAI_server(t, rh, fatal=True):  # @UnusedVariables
    """
    Send a JSON summary to DAVAI server.

    :param fatal: if False, catch errors, log but do not raise
    """
    server_syntax = 'http://<host>[:<port>]/<url> (port is optional)'
    try:
        summary = t.sh.json_load(rh.container.localpath())
        if rh.resource.kind == 'xpinfo':
            jsonData = {rh.resource.kind: summary}
        elif rh.resource.kind in ('taskinfo', 'statictaskinfo'):
            jsonData = {rh.provider.block: {rh.resource.scope: summary}}
        else:
            raise DavaiException("Only kind=('xpinfo','taskinfo', 'statictaskinfo') resources can be sent.")
        davai_server_url = t.env.get('DAVAI_SERVER')
        if davai_server_url == '':
            raise DavaiException("DAVAI_SERVER must be defined ! Expected syntax: " + server_syntax)
        else:
            if not davai_server_url.endswith('/api/'):
                davai_server_url = t.sh.path.join(davai_server_url, 'api', '')
            davai_server = uriparse(davai_server_url)
        if not t.sh.default_target.isnetworknode:
            # Compute node: open tunnel for send to target
            if davai_server['port'] is None:
                davai_server['port'] = 80
            # open tunnel
            sshobj = t.sh.ssh('network', virtualnode=True, maxtries=1,
                              mandatory_hostcheck=False)
            with sshobj.tunnel(davai_server['netloc'], int(davai_server['port'])) as tunnel:
                # 127.0.0.1 == localhost == tunnel entrance
                proxies = {'http': 'http://127.0.0.1:{}'.format(tunnel.entranceport)}
                send_task_to_DAVAI_server(davai_server_url,
                                          rh.provider.experiment,
                                          json.dumps(jsonData),
                                          kind=rh.resource.kind,
                                          fatal=fatal,
                                          proxies=proxies,
                                          headers={'Host': davai_server['netloc']})
        else:
            send_task_to_DAVAI_server(davai_server_url,
                                      rh.provider.experiment,
                                      json.dumps(jsonData),
                                      kind=rh.resource.kind,
                                      fatal=fatal,
                                      headers={'Host': davai_server['netloc']})
    except Exception as e:
        if fatal:
            raise
        else:
            logger.error(str(e))
