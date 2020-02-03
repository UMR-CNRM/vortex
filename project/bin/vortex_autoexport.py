#!/usr/bin/env python
# encoding: utf-8

"""
Exports Vortex to the many servers where it is installed.

This script exports a given version of Vortex. It extracts it from the Git
repository. Optionally, the current directory can be used as the source for the
Vortex code (but not recommended).

The servers that will recieve a copy of Vortex (the targets) are described in
a configuration file (see the ``--conf`` option)

For now, only the SSH export service is implemented.

"""

from __future__ import print_function, absolute_import, division, unicode_literals

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import logging
import os
import shutil
import re
import tempfile
import time
import subprocess
import traceback
from six.moves.configparser import SafeConfigParser
import pprint
import socket
import string
import sys
import uuid
import io

argparse_epilog = '''

Configuration file example:

[DEFAULT]
export_service  = SSH
username        = verolive
#keyfile        = /home/meunierlf/.ssh/id_rsa

[prolix]
#disabled       = True
hostname        = prolix.meteo.fr
stagingdir      = /home/mf/dp/marp/verolive/tmp/vortex_auto_unpack
headdir         = /home/mf/dp/marp/verolive/vortex
python27        = /opt/softs/python/2.7.5/bin/python

[beaufix]
#disabled       = True
hostname        = beaufix.meteo.fr
stagingdir      = /home/mf/dp/marp/verolive/tmp/vortex_auto_unpack
headdir         = /home/mf/dp/marp/verolive/vortex
python27        = /opt/softs/python/2.7.5/bin/python

Example:

# Export 0.9.22 version of Vortex on all the configured targets
{progname:s} 0.9.22

# Export the master branch of Vortex on beaufix only
{progname:s} master beaufix

# Create/Update a 'vortex-olive' link that will point to version 0.9.22
{progname:s} --link 0.9.22 olive

'''.format(progname=sys.argv[0])

logging.basicConfig()
logger = logging.getLogger()

_DEFAULT_ENCODING = sys.getdefaultencoding()

_TOOLBOX_PREFIX = 'vortex'

_VTXBASE = re.sub('{0:}project{0:}bin$'.format(os.path.sep), '',
                  os.path.dirname(os.path.realpath(__file__)))
_TEMPLATE_DIR = os.path.join(_VTXBASE, 'project', 'templates')


class ToolboxProvider(object):
    """Abstract class for a Toolbox provider."""

    _ALLOWED_VERSIONS = [re.compile(r'master$'),
                         re.compile(r'olive-(?:dev|ecmwf|lf)$'),
                         re.compile(r'cen[_-](?:dev|assim)$'),
                         re.compile(r'\d+\.\d+\.\d+$')]

    def __init__(self, tmpdir, wantedversion):
        """
        :param tmpdir: The temporary directory on the local host
        :param wantedversion: The requested version of the toolbox
        """
        self._tmpdir = tmpdir
        self._check_version(wantedversion)
        self._wantedversion = wantedversion

    def _check_version(self, wantedversion):
        for pattern in self._ALLOWED_VERSIONS:
            if pattern.match(wantedversion):
                return True
        raise ValueError("You are not allowed to request this version: " +
                         wantedversion)

    @property
    def _output_name(self):
        return '{:s}/{:s}-{:s}.tgz'.format(self._tmpdir, _TOOLBOX_PREFIX,
                                           self._wantedversion)

    def get_tar(self):
        """
        Create a tgz file that contains the Toolbox.

        The name of the tgz file is vortex-wantedversion. This tgz file contains
        a single directory also named vortex-wantedversion.

        :returns: str -- the full path to the tgz file.
        """
        raise NotImplementedError


class GitToolboxProvider(ToolboxProvider):
    """Uses Git to fetch a given version of the Toolbox."""

    _GIT_REPO_URI = 'reader066@git.cnrm-game-meteo.fr:/data/git/vortex.git'

    def _gitrun(self, cmd, *kargs):
        thecmd = ['git', cmd]
        thecmd.extend(kargs)
        logger.debug('Launching: ' + ' '.join(thecmd))
        try:
            output = subprocess.check_output(thecmd, stderr=subprocess.STDOUT,)
        except subprocess.CalledProcessError as e:
            output = e.output
            raise
        finally:
            if output:
                logger.debug("process output: \n" + output.decode(_DEFAULT_ENCODING,
                                                                  errors='ignore'))
        return output

    def _gitversion(self):
        if re.match(r'\d+\.\d+\.\d+$', self._wantedversion):
            return 'v{:s}'.format(self._wantedversion)
        else:
            return 'origin/{:s}'.format(self._wantedversion)

    def get_tar(self):
        tarprefix = 'vortex-{:s}'.format(self._wantedversion)
        tarname = re.sub('tgz', 'tar', self._output_name)
        os.chdir(self._tmpdir)
        logger.info("  Running git clone")
        self._gitrun('clone',
                     '--branch', self._gitversion().split('/')[-1],
                     self._GIT_REPO_URI, _TOOLBOX_PREFIX)
        os.chdir(os.path.join(self._tmpdir, 'vortex'))
        logger.info("  Running git archive")
        self._gitrun('archive',
                     '--prefix={:s}/'.format(tarprefix),
                     '-o', tarname, self._gitversion())
        logger.info("  Running git log, describe, and status")
        log = self._gitrun('log', '-100')
        desc = self._gitrun('describe')
        branch = self._gitrun('status')
        if log:
            logger.info("  Adding logfile to archive")
            os.chdir(self._tmpdir)
            os.makedirs(tarprefix)
            with io.open(os.path.join(self._tmpdir, tarprefix, 'README.gitlog'), 'wb') as fhlog:
                if branch:
                    fhlog.write(branch)
                    fhlog.write(b"\n")
                if desc:
                    fhlog.write(b"Last tag: " + desc)
                    fhlog.write(b"\n")
                fhlog.write(log)
            thecmd = ['tar', '-uf', tarname,
                      os.path.join(tarprefix, 'README.gitlog')]
            logger.debug('  Launching: ' + ' '.join(thecmd))
            subprocess.check_call(thecmd, shell=False)
        if re.match('.*gz$', self._output_name):
            logger.info("  Gzipping the archive")
            thecmd = ['gzip', tarname]
            logger.debug('Launching: ' + ' '.join(thecmd))
            subprocess.check_call(thecmd, shell=False)
            if tarname + '.gz' != self._output_name:
                thecmd = ['mv', tarname + '.gz', self._output_name]
                logger.debug('Launching: ' + ' '.join(thecmd))
                subprocess.check_call(thecmd, shell=False)
        return self._output_name


class LocalToolboxProvider(ToolboxProvider):
    """Uses the local directory to generate a version of the Toolbox."""

    def get_tar(self):
        for cdir in ['site', 'src']:
            if not os.path.isdir(cdir):
                raise ValueError("Incorrect source directory")
        thecmd = ['tar', "--transform=s/^[.]/{}-{}/".format(_TOOLBOX_PREFIX,
                                                            self._wantedversion),
                  '--exclude-backups', '--exclude=*.py[co]',
                  '--exclude=build', '--exclude=coverage_report',
                  '-czf', self._output_name, '.']
        logger.debug('Launching: ' + ' '.join(thecmd))
        subprocess.check_call(thecmd, shell=False)
        return self._output_name


class ExportServiceError(Exception):
    """Abstract exception for any ExportService."""
    pass


class ExportService(object):
    """Abstract class for an ExportService.

    An export service is in charge of transfering data on a remote host and
    launching commands on it.
    """

    def __init__(self, name, **kwargs):
        """
        :param **kwargs: parameters read from the configuration file.
        """
        self._internals = kwargs
        for k in ('python_p',
                  'ldlibrary_p', 'ldlibrary_p_python27', 'ldlibrary_p_python3'):
            if k in self._internals:
                self._internals[k] = self._internals[k].split(';')
        assert 'stagingdir' in self._internals
        assert 'python27' in self._internals or 'python3' in self._internals
        self._stagedir = None
        self._name = name

    def __del__(self):
        self.clean_stagedir()

    def __str__(self):
        return pprint.pformat(self._internals, indent=4)

    @property
    def name(self):
        return self._name

    def avail_py_versions(self):
        """Find out available python's interpreters (from the config file)."""
        avail = set()
        if 'python27' in self._internals:
            avail.add(2.7)
        if 'python3' in self._internals:
            avail.add(3)
        return avail

    def upload(self, local):
        """Transfer the local file on the remote host.

        It creates a temporary stage directory and returns the path to the
        uplodade file.

        :param local: Path to the local file that will be uploaded
        :returns: str -- Path to the uploaded file
        """
        raise NotImplementedError()

    def test_and_install(self, headdir, local, tmplocation):
        """Unpack the tar file, run test and install stuff.

        :param headir: The instalation headdir on the target host
        :param local: Path to the local file that was uploaded
        :param tmplocation: The temporary location of thee tar file (as returned
                            by :meth:`upload`)
        """
        raise NotImplementedError()

    def clean_stagedir(self):
        """Destroyed the temporary stage directory on the remote host."""
        raise NotImplementedError()

    def linkexport(self, source, headdir, dest):
        """Create a link from one vortex version to another."""
        raise NotImplementedError()

    def linkexport_stable(self, source, headdir):
        """Create a linkto vortex stable version."""
        raise NotImplementedError()


class ShellAccessExportService(ExportService):

    def sh_execute(self, cmd, onerror_raise=True, silent=False, catch_output=False):
        """Execute a shell command on the remote host.

        :param cmd: The command that will be launched
        :param onerror_raise: Should we raise an exception if `cmd` returns a bad exit code
        :param silent: Do we print the stdout/stderr of `cmd` if it fails
        :param catch_output: If True, stdout will be returned by the method (as an array of strings)
        :returns: bool or array of str: True/False depending on `cmd` exit code or stdout if catch_output=True
        """
        raise NotImplementedError()

    def py_execute(self, cmd, pythonpath=(), onerror_raise=True, silent=False,
                   catch_output=False, prefered_py=None):
        """Execute a python command on the remote host.

        :param cmd: The command that will be launched
        :param pythonpath: Value of this iterable will be added to the PYTHONPATH
        :param onerror_raise: Should we raise an exception if `cmd` returns a bad exit code
        :param silent: Do we print the stdout/stderr of `cmd` if it fails
        :param catch_output: If True, stdout will be returned by the method (as an array of strings)
        :param prefered_py: The prefered version for Python (if None, 2.7 will be used if available)
        :returns: bool or array of str: True/False depending on `cmd` exit code or stdout if catch_output=True
        """
        pythonpath = list(pythonpath)
        pythonpath.extend(list(self._internals.get('python_p', [])))
        ldlibrary_p_add = list(self._internals.get('ldlibrary_p', []))

        if ('python27' in self._internals and
                (prefered_py is None or prefered_py in ('27', '2.7', 2.7))):
            py27_ldlibrary_p_add = ldlibrary_p_add + list(self._internals.get('ldlibrary_p_python27', []))
            return self._py27_execute(self._internals['python27'], cmd,
                                      pysubs=dict(cversion='27', dversion='2.7'),
                                      pythonpath=pythonpath,
                                      ld_library_path=py27_ldlibrary_p_add,
                                      onerror_raise=onerror_raise, silent=silent,
                                      catch_output=catch_output)
        elif ('python3' in self._internals and
                (prefered_py is None or prefered_py in ('3', 3))):
            py3_ldlibrary_p_add = ldlibrary_p_add + list(self._internals.get('ldlibrary_p_python3', []))
            return self._py3_execute(self._internals['python3'], cmd,
                                     pysubs=dict(cversion='3', dversion='3'),
                                     pythonpath=pythonpath,
                                     ld_library_path=py3_ldlibrary_p_add,
                                     onerror_raise=onerror_raise, silent=silent,
                                     catch_output=catch_output)
        else:
            raise ValueError("Please specify a known python interpreter.")

    def _py27_execute(self, interp, cmd, pysubs, pythonpath=(), ld_library_path=(),
                      onerror_raise=True, silent=False, catch_output=False,
                      locale='fr_FR.UTF-8'):
        cmd_tr = ""
        if len(pythonpath) > 0:
            cmd_tr += 'export PYTHONPATH={}:$PYTHONPATH; '.format(':'.join(pythonpath))
        if len(ld_library_path) > 0:
            cmd_tr += 'export LD_LIBRARY_PATH={}:$LD_LIBRARY_PATH; '.format(':'.join(ld_library_path))
        if locale:
            cmd_tr += 'export LANG={!s}; '.format(locale)
        cmd_tr += ' '.join([interp, cmd])
        return self.sh_execute(cmd_tr.format(** pysubs), onerror_raise=onerror_raise, silent=silent,
                               catch_output=catch_output)

    _py3_execute = _py27_execute

    def upload(self, local):
        if not self._internals['stagingdir']:
            raise ValueError("The stagingdir configuration key is missing.")
        self.clean_stagedir()
        self.sh_execute('mkdir -p {}'.format(self._internals['stagingdir']))
        self._stagedir = self.sh_execute('mktemp -d --tmpdir={}'.format(self._internals['stagingdir']),
                                         catch_output=True)[0]
        destination = os.path.join(self._stagedir, os.path.basename(local))
        sftp = self._client.open_sftp()
        sftp.put(local, destination)
        return destination

    def test_and_install(self, headdir, local, tmplocation):
        # Utility stuff
        final_basename = os.path.basename(local).rstrip('.tgz')
        final_dir = os.path.join(headdir, final_basename)
        remote_tmpbase = os.path.dirname(tmplocation)
        remote_dir = os.path.join(remote_tmpbase, tmplocation.rstrip('.tgz'))
        enforce_check = bool(re.match('[Tt]rue',
                                      self._internals.get('enforce_check', 'True')))
        # Unpack it
        self.sh_execute("cd {}; tar -xzf {}".format(remote_tmpbase,
                                                    tmplocation))
        logger.info("  Tgz file uploaded and unpacked on {}".format(self.name))
        # Run the check (it will generate the pyc files)
        for pyv in self.avail_py_versions():
            self.py_execute("{0:s}/tests/do_working_tests-{{dversion:s}}.py".format(remote_dir),
                            pythonpath=('{0:s}/src'.format(remote_dir),
                                        '{0:s}/site'.format(remote_dir)),
                            onerror_raise=enforce_check,
                            prefered_py=pyv)
            logger.info("  make check was run on {} with python v{!s}.".format(self.name, pyv))
        # Prepare the destination directory
        self.sh_execute('mkdir -p {}'.format(headdir))
        # Test if one need to remove the previous version of the toolbox
        # Anyway, move the new version into the destination directory
        cleanup = self.sh_execute("test -e {}".format(final_dir),
                                  onerror_raise=False, silent=True)
        try:
            repl_cmd = ""
            if cleanup:
                repl_cmd += "mv {0:s} {0:s}.tmpdel; ".format(final_dir)
            repl_cmd += "mv {} {}; ".format(os.path.join(remote_tmpbase, final_basename),
                                            final_dir)
            self.sh_execute(repl_cmd)
            # Move the tar file next to the destination directory
            self.sh_execute('mv {} {}'.format(tmplocation, headdir))
        finally:
            # Remove the tmpdel directory
            if cleanup:
                repl_cmd = "rm -rf {0:s}.tmpdel".format(final_dir)
                if not self.sh_execute(repl_cmd, onerror_raise=False):
                    naptime = float(self._internals.get('sleep_retry', 2))
                    logger.warn('Waiting %s seconds and retries the delete...',
                                str(naptime))
                    time.sleep(naptime)
                    self.sh_execute(repl_cmd)
        logger.info("  The Vortex Toolbox was installed in {} on {}".format(final_dir,
                                                                            self.name))

    def clean_stagedir(self):
        """Destroyed the temporary stage directory on the remote host."""
        if self._stagedir is not None:
            self.sh_execute('rm -rf {}'.format(self._stagedir))
            self._stagedir = None

    def linkexport(self, source, headdir, dest):
        """Create a link from one vortex version to another."""
        self.sh_execute(('cd {0:s}; rm -f {1:s}-{3:s}; ' +
                         'ln -s {1:s}-{2:s} {1:s}-{3:s}').format(headdir,
                                                                 _TOOLBOX_PREFIX,
                                                                 source, dest))
        logger.info("  {1:s}-{3:s} -> {1:s}-{2:s} on {0:s}".format(self.name,
                                                                   _TOOLBOX_PREFIX,
                                                                   source, dest))

    def linkexport_stable(self, source, headdir):
        """Create a link from one vortex version to another."""
        self.sh_execute(('cd {0:s}; rm -f {1:s}; ' +
                         'ln -s {1:s}-{2:s} {1:s}').format(headdir,
                                                           _TOOLBOX_PREFIX,
                                                           source,))
        logger.info("  {1:s} -> {1:s}-{2:s} on {0:s}".format(self.name,
                                                             _TOOLBOX_PREFIX,
                                                             source))


class SSHExportServiceError(ExportServiceError):
    """Exception raised by the SSHExportService."""
    pass


class SSHExportService(ShellAccessExportService):
    """Export service based on SSH (using the paramiko package).

    The user will refer to the parent class documentation for a description of
    the public methods.
    """

    def __init__(self, name, **kwargs):
        super(SSHExportService, self).__init__(name, **kwargs)
        assert 'hostname' in self._internals
        assert 'username' in self._internals
        self.__theclient = None

    @property
    def _client(self):
        """Returns a valid SSH client (with an ative connection)."""
        if self.__theclient is None:
            import paramiko
            self.__theclient = paramiko.client.SSHClient()
            self.__theclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            extras = dict()
            if 'keyfile' in self._internals:
                extras['key_filename'] = self._internals['keyfile']
            self.__theclient.connect(self._internals['hostname'],
                                     username=self._internals['username'],
                                     **extras)
        return self.__theclient

    @staticmethod
    def _stream_process(stream):
        """Process return strings."""
        tmpstr = ''
        buf = True
        while buf:
            buf = stream(256)
            tmpstr += buf.decode(_DEFAULT_ENCODING, errors='ignore')
        tmpstr = tmpstr.rstrip("\n")
        return tmpstr.split("\n")

    def sh_execute(self, cmd, onerror_raise=True, silent=False, catch_output=False):
        ssh = self._client.get_transport().open_session()
        ssh.exec_command(cmd)
        exitcode = ssh.recv_exit_status()
        status = exitcode == 0
        stdout = self._stream_process(ssh.recv)
        stderr = self._stream_process(ssh.recv_stderr)
        # Error
        if (not status) and (not silent):
            logger.warn("Command: {}. Exit Code={:d}.".format(cmd, exitcode))
            logger.warn("Execution stdout: \n{}".format('\n'.join(stdout)))
            logger.warn("Execution stderr: \n{}".format('\n'.join(stderr)))
            if onerror_raise:
                raise SSHExportServiceError('Execution Error')
            else:
                logger.warn('Execution Error')
        else:
            # Execution was ok
            logger.debug("Command: {}. Exit Code={:d}.".format(cmd, exitcode))
            logger.debug("Execution stdout: \n{}".format('\n'.join(stdout)))
            logger.debug("Execution stderr: \n{}".format('\n'.join(stderr)))
        if catch_output:
            return stdout
        else:
            return status


class ScriptTemplate(string.Template):
    """A template that will substitute %{var} stuff (instead of ${var})."""
    delimiter = '%'


class EcAccessEcmwfExportServiceError(ExportServiceError):
    """Exception raised by the SSHExportService."""
    pass


class EcAccessEcmwfExportService(ExportService):
    """Export service based on EcAccess (needs to be updated).

    The user will refer to the parent class documentation for a description of
    the public methods.
    """

    _TEMPLATE_ID = None

    def __init__(self, name, **kwargs):
        if self._TEMPLATE_ID is None:
            raise NotImplementedError()
        super(EcAccessEcmwfExportService, self).__init__(name, **kwargs)
        assert 'hostname' in self._internals
        assert 'ecaccess_proxy' in self._internals
        assert 'ecaccess_proxy_stagingdir' in self._internals

    def _local_run(self, thecmd):
        logger.debug("running: " + ' '.join(thecmd))
        try:
            output = subprocess.check_output(thecmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            if output:
                logger.warn("process output: \n" + e.output.decode(_DEFAULT_ENCODING,
                                                                   errors='ignore'))
            raise EcAccessEcmwfExportServiceError('The << {!s} >> command failed.'.format(thecmd))
        else:
            if output:
                logger.debug("process output: \n" + output.decode(_DEFAULT_ENCODING,
                                                                  errors='ignore'))

    def upload(self, local):
        """Transfer the local file on the remote host.

        It creates a temporary stage directory and returns the path to the
        uplodade file.

        :param local: Path to the local file that will be uploaded
        :returns: str -- Path to the uploaded file
        """
        self._stagedtgz = uuid.uuid4().hex + '.' + os.path.basename(local)
        thecmd = ['ecaccess-file-put', local,
                  os.path.join(self._internals['ecaccess_proxy_stagingdir'], self._stagedtgz)]
        self._local_run(thecmd)
        return os.path.join(self._internals['ecaccess_proxy_stagingdir'], self._stagedtgz)

    def test_and_install(self, headdir, local, tmplocation):
        """Unpack the tar file, run test and install stuff.

        :param headir: The instalation headdir on the target host
        :param local: Path to the local file that was uploaded
        :param tmplocation: The temporary location of thee tar file (as returned
                            by :meth:`upload`)
        """
        batchsys = self._internals.get('batchsystem', 'default')
        batchtplname = 'autoexport_{}_head_{}.tpl'.format(self._TEMPLATE_ID, batchsys)
        with io.open(os.path.join(_TEMPLATE_DIR, batchtplname), 'rt', encoding='utf-8') as fhtpl:
            stpl = fhtpl.read()
        tplname = 'autoexport_{}_sync.tpl'.format(self._TEMPLATE_ID)
        with io.open(os.path.join(_TEMPLATE_DIR, tplname), 'rt', encoding='utf-8') as fhtpl:
            stpl += fhtpl.read()

        stpl = ScriptTemplate(stpl)

        ldlibrary_p_add = list(self._internals.get('ldlibrary_p', []))
        py27_ldlibrary_p_add = ldlibrary_p_add + list(self._internals.get('ldlibrary_p_python27', []))
        py3_ldlibrary_p_add = ldlibrary_p_add + list(self._internals.get('ldlibrary_p_python3', []))
        substuff = dict(jobname='vtxsync',
                        stagedir=self._internals['stagingdir'],
                        headdir=headdir,
                        local=local,
                        tmplocation=tmplocation,
                        tmphost=self._internals['ecaccess_proxy'],
                        python27=self._internals.get('python27', ''),
                        ldlibs27=':'.join(py27_ldlibrary_p_add),
                        python3=self._internals.get('python3', ''),
                        ldlibs3=':'.join(py3_ldlibrary_p_add))
        with tempfile.NamedTemporaryFile(mode='wt') as fhout:
            fhout.write(stpl.safe_substitute(substuff))
            fhout.flush()
            thecmd = ['ecaccess-job-submit', '-eo', '-onFailure', '-queueName', self._internals['hostname'], fhout.name]
            self._local_run(thecmd)
        logger.info("  Synchronisation script launched on %s based on template: %s",
                    self.name, tplname)

    def clean_stagedir(self):
        """Destroyed the temporary stage directory on the remote host."""
        # Cleanup will be handled by the export job itself...
        pass

    def _raw_linkexport(self, source, headdir, dest):
        """Create a link from one vortex version to another."""
        batchsys = self._internals.get('batchsystem', 'default')
        batchtplname = 'autoexport_{}_head_{}.tpl'.format(self._TEMPLATE_ID, batchsys)
        with io.open(os.path.join(_TEMPLATE_DIR, batchtplname), 'rt', encoding='utf-8') as fhtpl:
            stpl = fhtpl.read()
        tplname = 'autoexport_{}_link.tpl'.format(self._TEMPLATE_ID)
        with io.open(os.path.join(_TEMPLATE_DIR, tplname), 'rt', encoding='utf-8') as fhtpl:
            stpl += fhtpl.read()

        stpl = ScriptTemplate(stpl)

        substuff = {'jobname': 'vtxlink', 'headdir': headdir, 'from': source, 'to': dest, }
        with tempfile.NamedTemporaryFile(mode='wt') as fhout:
            fhout.write(stpl.safe_substitute(substuff))
            fhout.flush()
            thecmd = ['ecaccess-job-submit', '-queueName', self._internals['hostname'], fhout.name]
            self._local_run(thecmd)
        logger.info("  Linking script launched on %s based on template: %s",
                    self.name, tplname)

    def linkexport(self, source, headdir, dest):
        """Create a link from one vortex version to another."""
        return self._raw_linkexport('{}-{}'.format(_TOOLBOX_PREFIX, source), headdir,
                                    '{}-{}'.format(_TOOLBOX_PREFIX, dest))

    def linkexport_stable(self, source, headdir):
        """Create a link to vortex stable version."""
        return self._raw_linkexport('{}-{}'.format(_TOOLBOX_PREFIX, source), headdir,
                                    _TOOLBOX_PREFIX)


class EcmwfV1ExportService(EcAccessEcmwfExportService):
    """Export service based on EcAccess + V1 deployment scripts.

    The user will refer to the parent class documentation for a description of
    the public methods.
    """

    _TEMPLATE_ID = 'ecmwfv1'


class ExportTarget(object):
    """Defines a Target where Vortex is installed."""

    def __init__(self, name, **kwargs):
        """
        :param name: A nickname for this target.
        :param **kwargs: Parameters read from the configuration file.
        """

        self._name = name

        if 'headdir' not in kwargs:
            raise ValueError('The headdir configuration key is missing.')
        self._headdir = kwargs.pop('headdir')

        logger.debug("Target {}: headdir={}".format(self._name, self._headdir))

        # Instantiate the export service
        exp_service_kind = kwargs.pop('export_service', 'SSH')
        self._exp = globals()[exp_service_kind + 'ExportService'](self._name, **kwargs)
        logger.info("Target {}: Using the {} export service.".format(self._name,
                                                                     exp_service_kind))
        logger.debug("Target {}: Export service is: \n{!s}".format(self._name, self._exp))

    @property
    def name(self):
        return self._name

    def autoexport(self, local):
        """Export the Vortex copy contained in `local`.

        :param enforce_check: If False, a error on make check won't be fatal
        """
        remote_tgz = self._exp.upload(local)
        try:
            self._exp.test_and_install(self._headdir, local, remote_tgz)
        finally:
            self._exp.clean_stagedir()

    def linkexport(self, source, dest):
        """Create a link from one vortex version to another."""
        self._exp.linkexport(source, self._headdir, dest)

    def linkexport_stable(self, source):
        """Create a link from one vortex version to another."""
        self._exp.linkexport_stable(source, self._headdir)


def main():
    """Process command line options."""

    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc

    # Setup argument parser
    parser = ArgumentParser(description=program_desc, epilog=argparse_epilog,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("version",
                        help="The version of Vortex that will be exported")
    parser.add_argument("targets", nargs='*',
                        help="Vortex will be exported to... (all targets if omitted).")
    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        default=0, help="Set verbosity level [default: %(default)s]")
    parser.add_argument("-t", "--tmpdir", dest="tmpdir",
                        default=os.environ.get('VORTEX_AUTOEXPORT_TMPDIR',
                                               os.environ['HOME'] + '/tmp'),
                        help="Directory hosting the temporary Git clone or " +
                             "Tar file on the local host [default: %(default)s]")
    parser.add_argument("-c", "--conf", dest="conf",
                        default=os.environ.get('VORTEX_AUTOEXPORT_CONF',
                                               os.environ['HOME'] + '/.vortex_autoexport.conf'),
                        help="Path to the targets configuration file [default: %(default)s]")
    grpexc = parser.add_mutually_exclusive_group()
    grpexc.add_argument("--link", dest="link", action="store", default="",
                        help="Just create a link to the designated version.")
    grpexc.add_argument("--setstable", dest="stable", action="store_true",
                        help="Set the designated version as the latest stable.")
    grpexc.add_argument("--local", dest="local", action="store_true",
                        help="Uses the current directory as a source for Vortex " +
                             "instead of a Git clone.")

    # Process arguments
    args = parser.parse_args()

    # Setup logger verbosity
    log_levels = {0: ('INFO', 'WARNING'), 1: ('DEBUG', 'INFO'),
                  2: ('DEBUG', 'DEBUG'), }
    mylog_levels = log_levels.get(args.verbose, ('DEBUG', 'DEBUG'))
    logger.setLevel(mylog_levels[0])
    miko_logs = logging.getLogger('paramiko')
    miko_logs.setLevel(mylog_levels[1])

    # Load the configuration file and create the targets
    targets = dict()
    cparser = SafeConfigParser()
    cparser.read(args.conf)
    for section in cparser.sections():
        if ((len(args.targets) == 0 and
                not (cparser.has_option(section, 'disabled') and
                     cparser.getboolean(section, 'disabled'))) or
                section in args.targets):
            targets[section] = ExportTarget(section, ** dict(cparser.items(section)))

    # Just in case we need a temp directory
    thedir = tempfile.mkdtemp(prefix='tmp_vortex_export_', dir=args.tmpdir)

    try:

        # We do not need to generate a Tar if only a link is needed
        if not (args.link or args.stable):
            # Create the Vortex tar file
            if args.local:
                logger.info("The vortex Tgz will be generated from the current directory")
                prv = LocalToolboxProvider(thedir, args.version)
            else:
                logger.info("The vortex Tgz will be generated from Git")
                prv = GitToolboxProvider(thedir, args.version)
            thetgz = prv.get_tar()
            logger.debug("The vortex tgz on the local host is: " + thetgz)
            logger.info("The vortex Tgz has been generated :-)\n")

        # Export !
        failed_list = list()
        for dest in targets.values():
            try:
                if args.link:
                    logger.info("Updating links on {}".format(dest.name))
                    dest.linkexport(args.link, args.version)
                elif args.stable:
                    logger.info("Updating links on {}".format(dest.name))
                    dest.linkexport_stable(args.version)
                else:
                    logger.info("Exporting the Vortex Toolbox to {}".format(dest.name))
                    dest.autoexport(thetgz)
            except (ExportServiceError, socket.error) as e:
                logger.error("Export failed for < %s >: %s. %s",
                             dest.name, str(e), traceback.format_exc())
                failed_list.append(dest.name)
            else:
                logger.info("We are done with %s !\n", dest.name)
        if failed_list:
            logger.error("Some of the exports failed: %s", ",".join(failed_list))

    finally:
        # Destroy the tmp dir
        logger.debug("Deleting the tmp directory on the local host: " + thedir)
        shutil.rmtree(thedir)


if __name__ == "__main__":
    sys.exit(main())
