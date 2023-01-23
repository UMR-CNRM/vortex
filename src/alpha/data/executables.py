"""
TODO: Module documentation
"""

from bronx.fancies import loggers

from vortex.data.executables import Script

from gco.syntax.stdattrs import gvar

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class AlphaPythonScript(Script):
    """These scripts are useful to compute Alpha prod and handle grib inputs."""

    _footprint = [
        gvar,
        dict(
            attr = dict(
                kind = dict(
                    values = ['prod', 'manager', 'traitement', 'amendements']
                ),
                language = dict(
                    default = 'python',
                ),
                gvar = dict(
                    default = 'ALPHA_EXE_[kind]',
                ),
                vconf = dict(
                    values = ['france_jj1', 'france_j2j3', 'monde_jj1', 'monde_j2j3',
                              'antilles_jj1', 'caledonie_jj1', 'polynesie_jj1', 'guyane_jj1',
                              'mayotte_jj1', 'reunion_jj1', ]
                ),
            )
        )
    ]

    def command_line(self, **kw):
        return kw['command_line']


class AlphaShellScript(Script):
    """This script launch alpha prod and amandements."""

    _footprint = [
        gvar,
        dict(
            attr = dict(
                kind = dict(
                    values = ['launch']
                ),
                gvar = dict(
                    default = 'ALPHA_SRC_[kind]',
                ),
                vconf = dict(
                    values = ['france_jj1', 'france_j2j3', 'monde_jj1', 'monde_j2j3',
                              'antilles_jj1', 'caledonie_jj1', 'polynesie_jj1', 'guyane_jj1',
                              'mayotte_jj1', 'reunion_jj1']
                ),
                domain = dict(
                    values = ['France', 'Monde', 'OM', 'Reunion']
                ),
            )
        )
    ]

    def command_line(self, **kw):
        return kw['command_line']
