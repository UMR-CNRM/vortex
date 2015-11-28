#!/usr/bin/env python
# -*- coding: utf-8 -*-

import footprints

from vortex.data.stores import Store
from vortex.tools import date
from vortex.syntax.stdattrs import DelayedEnvValue

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class AgtConfigurationError(Exception):
    """Specific Transfer Agent configuration error."""
    pass


def agt_actual_command(sh, binary_name, args):
    """Build the command able to execute a Transfer Agent binary.

    The context, the execution path and the command name are
    provided by the configuration file of the target.

    The resulting command should be executed on a transfer node.
    """
    config = sh.target().config
    if not config.has_section('agt'):
        fmt = 'Missing section "agt" in configuration file\n"{}"'
        raise AgtConfigurationError(fmt.format(config.file))

    agt_path = sh.target().get('agt_path', default=None)
    agt_bin  = sh.target().get(binary_name, default=None)
    if not all([agt_path, agt_bin]):
        fmt = 'Missing key "agt_path" or "{}" in configuration file\n"{}"'
        raise AgtConfigurationError(fmt.format(binary_name, config.file))

    context = ' ; '.join(["export {}={}".format(key.upper(), value)
                          for (key, value) in config.items('agt')])
    return '{} ; {} {}'.format(context, sh.path.join(agt_path, agt_bin), args)


class BdpeStore(Store):
    """Access items stored in the BDPE database (get only)."""

    _footprint = dict(
        info = 'Access the BDPE database',
        attr = dict(
            scheme = dict(
                values   = ['bdpe'],
            ),
            netloc = dict(
                values   = ['bdpe.archive.fr'],
            ),
            store_preferred_target = dict(
                optional = True,
                default  = DelayedEnvValue('BDPE_CIBLE_PREFEREE', 'OPER'),
                values   = ['OPER', 'INT', 'SEC', 'DEV'],
            ),
            store_forbidden_target = dict(
                optional = True,
                default  = DelayedEnvValue('BDPE_CIBLE_INTERDITE', 'DEV'),
                values   = ['OPER', 'INT', 'SEC', 'DEV'],
            ),
        ),
        priority = dict(
            level = footprints.priorities.top.DEFAULT
        )
    )

    @property
    def realkind(self):
        return 'bdpe'

    def bdpelocate(self, remote, options):
        """Reasonably close to whatever 'remote location' could mean.
           e.g.: bdpe://bdpe.archive.fr/EXPE/date/BDPE_num+term
        """
        return self.scheme + '://' + self.netloc + remote['path']

    def bdpecheck(self, remote, options):
        """Cannot check a BDPE call a priori."""
        logger.warning("A BdpeStore is not able to perform CHECKs.")
        return False

    def bdpeput(self, local, remote, options):
        """Cannot wrte to the BDPE (yet ?)."""
        logger.error("A BdpeStore is not able to perform PUTs.")
        return False

    def bdpedelete(self, remote, options):
        """Cannot delete a BDPE product."""
        logger.error("A BdpeStore is not able to perform DELETEs.")
        return False

    def bdpeget(self, remote, local, options):
        """Real extraction from the BDPE database."""

        # remote['path'] looks like '/86GV/20151105T0000P/BDPE_42+06:00'
        _, experiment, str_date, more = remote['path'].split('/')
        productid, str_term = more[5:].split('+')
        args = '{id} {date} {term} {local}'.format(
            id    = productid,
            date  = date.Date(str_date).ymdhms,  # yyyymmddhhmmss
            term  = date.Time(str_term).fmtraw,  # HHHHmm
            local = local,
        )
        actual_command = agt_actual_command(self.system, 'agt_lirepe', args)

        # TODO appel lirepe
        #    - ajouter BDPE_CIBLE_PREFEREE et BDPE_CIBLE_INTERDITE dans l'env
        #    - executer sur un nœud de transfer (service ssh, Cf.
        #      ad.ssh dans iga/tools/services.py::431)
        #    - mais le résultat est un fichier **local** et la bdpe
        #      n'écrit pas dans un pipe
        #    - lirepe retourne $? == 0 pour "arguments ok", >0 sinon
        #    - et si erreur d'exécution, ou produit manquant ?
        #      Vérifier, et/ou s'il manque, montrer le contenu du fichier
        #      de diagnostique (output_demandé + '.diag')
        #    - utiliser ce agt_actual_command pour simplifier ce qui
        #      est fait dans iga/tools/services.py:
        #        * RoutingService.agt_env()
        #        * BdpeService.actual_agt_pe_cmd()
        #        * RoutingUpstreamService.actual_agt_pa_cmd()

        # plpl debug
        self.system.title('bdpeget')
        print 'remote : {}'.format(remote)
        print 'local  : {}'.format(local)
        # print 'options: {}'.format(options)
        print
        print 'actual_command =', actual_command

        return True
