# -*- coding: utf-8 -*-

"""
System Addons to support ECMWF' ECFS archiving system.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import contextlib
import io
import re
import six
import tempfile

from bronx.fancies import loggers
import footprints

from vortex.tools import addons
from vortex.tools.systems import fmtshcmd
from .interfaces import ECfs

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def use_in_shell(sh, **kw):
    """Extend current shell with the ECfs interface defined by optional arguments."""
    kw['shell'] = sh
    return footprints.proxy.addon(**kw)


class ECfsError(Exception):
    """Generic ECfs error"""
    pass


class ECfsConfigurationError(ECfsError):
    """Generic ECfs configuration error"""
    pass


class ECfsTools(addons.Addon):
    """
    Handle ECfs use properly within Vortex.
    """
    _footprint = dict(
        info = 'Default ECfs system interface',
        attr = dict(
            kind = dict(
                values   = ['ecfs'],
            ),
        )
    )

    def ecfstest(self, item, options=None):
        """Test a state of the file provided using ECfs.

        :param item: file to be tested
        :param options: list of options to be used by the test (default "r": test existence)
        :return: return code
        """
        ecfs = ECfs(system=self.sh)
        command = "etest"
        list_args = [item, ]
        if options is None:
            list_options = ["r", ]
        else:
            list_options = options
        rc = ecfs(command=command,
                  list_args=list_args,
                  dict_args=dict(),
                  list_options=list_options,
                  fatal=False, silent=True)
        return rc

    def ecfschmod(self, mode, location, options=None):
        """Change permissions on the location using Ecfs.

        :param mode: The new permissions (UNIX style e.g. 644)
        :param location: target file
        :param options: list of options to be used (default none)
        :return: return code
        """
        ecfs = ECfs(system=self.sh)
        command = "echmod"
        list_args = [mode, location]
        if options is None:
            list_options = list()
        else:
            list_options = options
        return ecfs(command=command,
                    list_args=list_args,
                    dict_args=dict(),
                    list_options=list_options)

    def ecfsls(self, location, options):
        """List the files at a location using ECfs.

        :param location: location the contents of which should be listed
        :param options: list of options to be used (default: "1").
        :return: return code
        """
        ecfs = ECfs(system=self.sh)
        command = "els"
        list_args = [location, ]
        if options is None:
            list_options = ["1", ]
        else:
            list_options = options
        rc = ecfs(command=command,
                  list_args=list_args,
                  dict_args=dict(),
                  list_options=list_options,
                  capture=True, silent=True)
        return rc

    def ecfsmkdir(self, target, options=None):
        """Recursively creates sub-directories.

        :param target: target subdirectory
        :param options: list of options to be used (default none)
        :return: return code
        """
        ecfs = ECfs(system=self.sh)
        command = " emkdir"
        list_args = [target, ]
        list_options = list()
        if isinstance(options, list):
            list_options = options
        if not list_options:
            list_options.append('p')
        return ecfs(command=command,
                    list_args=list_args,
                    dict_args=dict(),
                    list_options=list_options)

    @contextlib.contextmanager
    def _ecfspath_normalize(self, path, intent='in'):
        if intent not in {'in', 'out'}:
            raise ValueError('Improper value for intent.')
        if not re.match(r'^ec\w*:', path) and ':' in path:
            tmpdir = tempfile.mkdtemp(prefix='ecfs_pnorm_')
            try:
                target = self.sh.path.join(tmpdir, 'normalized')
                if intent == 'in':
                    logger.debug("Temporary remapping of %s to %s (because of ECFS filename restrictions)",
                                 path, target)
                    self.sh.softlink(path, target)
                else:
                    logger.debug("Temporary file created: %s (because of ECFS filename restrictions)",
                                 target)
                yield target
                if intent == 'out':
                    logger.debug("Moving temporary file %s to %s", target, path)
                    self.sh.mv(target, path)
            finally:
                self.sh.remove(tmpdir)
        else:
            yield path

    @contextlib.contextmanager
    def _ecfscp_xsource(self, source):
        if isinstance(source, six.string_types):
            with self._ecfspath_normalize(source) as source:
                yield source
        else:
            with tempfile.NamedTemporaryFile('w+b') as fhtmp:
                source.seek(0)
                self.sh.copyfileobj(source, fhtmp)
                fhtmp.flush()
                yield fhtmp.name

    @contextlib.contextmanager
    def _ecfscp_xtarget(self, target):
        if isinstance(target, six.string_types):
            with self._ecfspath_normalize(target, intent='out') as target:
                yield target
        else:
            with tempfile.NamedTemporaryFile('w+b') as fhtmp:
                yield fhtmp.name
                with io.open(fhtmp.name, 'rb') as fhtmp2:
                    self.sh.copyfileobj(fhtmp2, target)

    @fmtshcmd
    def ecfscp(self, source, target, options=None):
        """Copy the source file to the target using Ecfs.

        :param source: source file to be copied
        :param target: target file
        :param options: list of options to be used (default none)
        :return: return code
        """
        ecfs = ECfs(system=self.sh)
        command = "ecp"
        with self._ecfscp_xsource(source) as source:
            with self._ecfscp_xtarget(target) as target:
                list_args = [source, target]
                list_options = list()
                if isinstance(options, list):
                    list_options = options
                if {'e', 'n', 'u', 't'}.isdisjoint(set(list_options)):
                    list_options.append('o')
                rc = ecfs(command=command,
                          list_args=list_args,
                          dict_args=dict(),
                          list_options=list_options)
        return rc

    @fmtshcmd
    def ecfsget(self, source, target, cpipeline=None, options=None):
        """Get a resource using ECfs (default class).

        :param source: file to be copied
        :param target: target file
        :param cpipeline: compression pipeline used, if provided
        :param options: options to be used
        :return: return code
        """
        if cpipeline is None:
            return self.ecfscp(source=source,
                               target=target,
                               options=options)
        else:
            ctarget = target + self.sh.safe_filesuffix()
            try:
                rc, dict_args = self.ecfscp(source=source,
                                            target=ctarget,
                                            options=options)
                rc = rc and cpipeline.file2uncompress(source=ctarget,
                                                      destination=target)
            finally:
                self.sh.rm(ctarget)
            return rc

    @fmtshcmd
    def ecfsput(self, source, target, cpipeline=None, options=None):
        """Put a resource using ECfs (default class).

        :param source: file to be copied
        :param target: target file
        :param cpipeline: compression pipeline used, if provided
        :param options: options to be used
        :return: return code
        """
        if cpipeline is None:
            return self.ecfscp(source=source,
                               target=target,
                               options=options)
        else:
            csource = source + self.sh.safe_filesuffix()
            try:
                rc1 = cpipeline.compress2file(source=source,
                                              target=csource)
                rc = self.ecfscp(source=csource, target=target, options=options)
            finally:
                self.sh.rm(csource)
            rc = rc and rc1
            return rc

    @fmtshcmd
    def ecfsrm(self, item, options):
        """Delete a file or directory using ECfs.

        :param item: file or directory to be deleted
        :param options: list of options to be used (default none)
        :return: return code
        """
        ecfs = ECfs(system=self.sh)
        command = "erm"
        list_args = [item, ]
        if options is None:
            list_options = list()
        else:
            list_options = options
        if ecfs:
            rc = ecfs(command=command,
                      list_args=list_args,
                      dict_args=dict(),
                      list_options=list_options)
        return rc
