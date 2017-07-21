#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.layout.nodes import Task
from vortex.tools.actions import actiond as ad


class OpTask(Task):
    """Wrapper for setting up and performing a miscellaneous op task for a serial execution."""

    _tag_topcls = False

    def report_execution_error(self):
        reseau    = self.conf.rundate.hh
        logpath   = self.env.LOG
        rundir    = self.env.getvar('RUNDIR') + '/opview/' + self.tag
        listing   = rundir + '/NODE.001_01'
        vapp      = self.env.getvar('OP_VAPP').upper()
        vconf     = self.env.getvar('OP_VCONF').lower()
        xpid      = self.env.getvar('OP_XPID').lower()
        hasmember = self.env.getvar('OP_HASMEMBER')
        if hasmember:
            member    = self.env.getvar('OP_MEMBER')
            self.sh.header('Send a mail due to an execution error')
            subject = "{0:s} {1:s} {2:s} : Problème d'execution ({3:s} du membre {4:s} pour le réseau de {5:s}h).".format(xpid.upper(),vapp,vconf,self.tag,str(member),reseau)
            msg     = "L'exécution de la tâche {0:s} du membre {1:s} du réseau {2:s}h du modèle {3:s}-{4:s} a échoué".format(self.tag, str(member), reseau, vapp, vconf)  
            ad.opmail(subject=subject, msg=msg, report="", reseau=reseau, task=self.tag, member=str(member), id ='error', log=logpath, rundir=rundir, listing=listing, vapp=vapp, vconf=vconf, xpid=xpid)
            raise
        else:
            self.sh.header('Send a mail due to an execution error')
            subject = "{0:s} {1:s} {2:s} : Problème d'execution ({3:s} du réseau {4:s}h).".format(xpid.upper(),vapp,vconf,self.tag,reseau)
            msg     = "L'exécution de la tâche {0:s} pour le réseau {1:s}h du modèle {2:s}-{3:s} a échoué".format(self.tag, reseau, vapp, vconf)
            ad.opmail(subject=subject, msg=msg, report="", reseau=reseau, task=self.tag, id ='error', log=logpath, rundir=rundir, listing=listing, vapp=vapp, vconf=vconf, xpid=xpid)
            raise

    def defaults(self, extras):
        """Set defaults for toolbox defaults, with priority to actual conf."""
        extras.setdefault('namespace', self.conf.get('namespace', 'vortex.cache.fr'))
        extras.setdefault('gnamespace', self.conf.get('gnamespace', 'opgco.cache.fr'))
        super(OpTask, self).defaults(extras)

    def __exit__(self, exc_type, exc_value, traceback):
        """Cleanup promises on exit."""
        # Note: If an MTOOL like tool was to be used, this should be changed...
        self.ticket.context.clear_promises()
        super(OpTask, self).__exit__(exc_type, exc_value, traceback)


class OpTaskMPI(OpTask):
    """Wrapper for setting up and performing a miscellaneous op task for an MPI execution.

    This is now useless (kept for backward compatibility)
    """

    _tag_topcls = False
