#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Standard services to be used by user defined actions.
With the abstract class Service (inheritating from FootprintBase)
a default Mail Service is provided.
"""

#: No automatic export
__all__ = []

import os
import random
import base64

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import sessions
from vortex.tools import date

from vortex.tools.actions import actiond as ad


# See logging.handlers.SysLogHandler.priority_map
criticals = ['debug', 'info', 'error', 'warning', 'critical']


class Service(footprints.FootprintBase):
    """
    Abstract base class for services.
    """

    _abstract  = True
    _collector = ('service',)
    _footprint = dict(
        info = 'Abstract services class',
        attr = dict(
            kind = dict(),
            level = dict(
                optional = True,
                default  = 'info',
                values   = criticals,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract service init %s', self.__class__)
        sh = kw.pop('sh', sessions.system())
        super(Service, self).__init__(*args, **kw)
        self._sh = sh

    @property
    def realkind(self):
        return 'service'

    @property
    def sh(self):
        return self._sh

    @property
    def env(self):
        return self._sh.env


    def actual_value(self, key, as_var=None, as_conf=None, default=None):
        """
        Return for a given ``attr`` a value from several sources in turn:
        - a defined attribute value (e.g. from the footprint)
        - a shell environment variable
        - a variable from an ini file section
        - a default value as specified.
        """
        if as_var is None:
            as_var = key.upper()
        value = getattr(self, key, self.env.get(as_var, None))
        if not value:
            if as_conf is None:
                as_conf = 'services:' + key.lower()
            value = self.sh.target().get(as_conf, default)
        return value

    def __call__(self, *args):
        pass


class MailService(Service):
    """
    Class responsible for handling email data.
    This class should not be called directly.
    """

    _footprint = dict(
        info = 'Mail services class',
        attr = dict(
            kind = dict(
                values   = ['sendmail'],
            ),
            sender = dict(
                optional = True,
                default  = '[glove::xmail]',
            ),
            to = dict(
                alias    = ('receiver', 'recipients'),
            ),
            replyto = dict(
                optional = True,
                alias    = ('reply', 'reply_to'),
                default  = None,
            ),
            message = dict(
                optional = True,
                default  = '',
                alias    = ('contents', 'body'),
            ),
            filename = dict(
                optional = True,
                default  = None,
            ),
            attachments = dict(
                type     = footprints.FPList,
                optional = True,
                default  = footprints.FPList(),
                alias    = ('files', 'attach'),
            ),
            subject = dict(),
            smtpserver = dict(
                optional = True,
                default  = 'localhost',
            ),
            altmailx = dict(
                optional = True,
                default  = '/usr/sbin/sendmail',
            ),
            charset = dict(
                optional = True,
                default  = 'utf-8',
            ),
            commaspace = dict(
                optional = True,
                default  = ', '
            )
        )
    )

    def attach(self, *args):
        """Extend the internal attachments of the next mail to send."""
        self.attachments.extend(args)
        return len(self.attachments)

    @staticmethod
    def is_not_plain_ascii(string):
        return not all(ord(c) < 128 for c in string)

    def get_message_body(self):
        """Returns the internal body contents as a MIMEText object."""
        body = self.message
        if self.filename:
            with open(self.filename, 'r') as tmp:
                body += tmp.read()
        mimetext = self.get_mimemap().get('text')
        if self.is_not_plain_ascii(body):
            return mimetext(body.decode(self.charset), 'plain', self.charset)
        else:
            return mimetext(body, 'plain')

    def get_mimemap(self):
        """Construct and return a map of MIME types."""
        try:
            md = self._mimemap
        except AttributeError:
            from email.mime.audio import MIMEAudio
            from email.mime.image import MIMEImage
            from email.mime.text import MIMEText
            self._mimemap = dict(
                text  = MIMEText,
                image = MIMEImage,
                audio = MIMEAudio
            )
        finally:
            return self._mimemap

    def as_multipart(self, msg):
        """Build a new multipart mail with default text contents and attachments."""
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        multi = MIMEMultipart()
        multi.attach(msg)
        for xtra in self.attachments:
            if isinstance(xtra, MIMEBase):
                multi.attach(xtra)
            elif os.path.isfile(xtra):
                import mimetypes
                ctype, encoding = mimetypes.guess_type(xtra)
                if ctype is None or encoding is not None:
                    # No guess could be made, or the file is encoded (compressed), so
                    # use a generic bag-of-bits type.
                    ctype = 'application/octet-stream'
                maintype, subtype = ctype.split('/', 1)
                mimemap = self.get_mimemap()
                mimeclass = mimemap.get(maintype, None)
                if mimeclass:
                    fp = open(xtra)
                    xmsg = mimeclass(fp.read(), _subtype=subtype)
                    fp.close()
                else:
                    xmsg = MIMEBase(maintype, subtype)
                    fp = open(xtra, 'rb')
                    xmsg.set_payload(fp.read())
                    fp.close()
                xmsg.add_header('Content-Disposition', 'attachment', filename=xtra)
                multi.attach(xmsg)
        return multi

    def set_headers(self, msg):
        """Put on the current message the header items associated to footprint attributes."""
        msg['From']     = self.sender
        msg['To']       = self.commaspace.join(self.to.split())
        msg['Subject']  = self.subject
        if self.replyto is not None:
            msg['Reply-To'] = self.commaspace.join(self.replyto.split())

    def __call__(self):
        """Main action: pack the message body, add the attachments, and send via SMTP."""
        msg = self.get_message_body()
        if self.attachments:
            msg = self.as_multipart(msg)
        self.set_headers(msg)
        msgcorpus = msg.as_string()
        if self.sh.target().generic().endswith('cn'):
            import tempfile
            count, tmpmsgfile = tempfile.mkstemp(prefix='mailx_')
            with open(tmpmsgfile, 'w') as fd:
                fd.write(msgcorpus)
            mailcmd = '{0:s} {1:s} < {2:s}'.format(
                self.altmailx,
                ' '.join(self.to.split()),
                tmpmsgfile
            )
            ad.ssh(mailcmd, hostname='node', nodetype='login')
            self.sh.remove(tmpmsgfile)
        else:
            import smtplib
            smtp = smtplib.SMTP(self.smtpserver)
            smtp.sendmail(self.sender, self.to.split(), msgcorpus)
            smtp.quit()
        return len(msgcorpus)


class ReportService(Service):
    """
    Class responsible for handling report data.
    This class should not be called directly.
    """

    _abstract = True
    _footprint = dict(
        info = 'Report services class',
        attr = dict(
            kind = dict(
                values   = ['sendreport']
            ),
            sender = dict(
                optional = True,
                default  = '[glove::user]',
            ),
            subject = dict(
                optional = True,
                default  = 'Test'
            ),
        )
    )

    def __call__(self, *args):
        """Main action: ..."""
        pass


class FileReportService(ReportService):
    """Building the report as a simple file."""

    _footprint = dict(
        info = 'File Report services class',
        attr = dict(
            kind = dict(
                values = ['sendreport', 'sendfilereport'],
                remap  = dict(sendfilereport = 'sendreport'),
            ),
            filename = dict(),
        )
    )

class SSHProxy(Service):
    """
    Remote execution via ssh on a generic target.
    If ``node`` is the specified hostname value, some target hostname
    will be built on the basis of attributes ,``nodebase``, ``nodetype`` and ``noderange``.
    In that case, hostname = nodebase + nodetype + nodenumber.
    The nodenumber is taken as the first value in noderange, with random permutation or not.
    """

    _footprint = dict(
        info = 'Remote command proxy',
        attr = dict(
            kind = dict(
                values   = ['ssh', 'ssh_proxy'],
                remap    = dict(autoremap = 'first'),
            ),
            hostname = dict(),
            nodebase = dict(
                optional = True,
                default  = None,
                access   = 'rwx',
            ),
            nodetype = dict(
                optional = True,
                values   = ['login', 'transfert'],
                default  = 'login',
            ),
            noderange = dict(
                optional = True,
                type     = footprints.FPList,
                default  = None,
            ),
            permut = dict(
                type     = bool,
                optional = True,
                default  = True,
            ),
            maxtries = dict(
                type     = int,
                optional = True,
                default  = 2,
            ),
            sshcmd = dict(
                optional = True,
                default  = '/usr/bin/ssh',
            ),
            sshopts = dict(
                optional = True,
                type     = footprints.FPList,
                default  = footprints.FPList(['-x']),
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Remote command proxy init %s', self.__class__)
        super(SSHProxy, self).__init__(*args, **kw)
        self._retries = None

    @property
    def retries(self):
        return self._retries

    def build_targets(self):
        """Build a list of candidate target hostnames."""
        targets = [ self.hostname.strip().lower() ]
        if targets[0] == 'node':
            nodebase  = self.nodebase  or self.actual_value('ssh' + self.nodetype + 'base', default=self.sh.target().inetname)
            noderange = self.noderange or self.actual_value('ssh' + self.nodetype + 'range')
            if noderange is None:
                noderange = ('',)
            else:
                if isinstance(noderange, basestring):
                    noderange = [ x.strip() for x in noderange.split(',') ]
                if self.permut:
                    noderange = list(noderange)
                    random.shuffle(noderange)
            targets = [ nodebase + self.nodetype + str(x) for x in noderange ]
        return targets

    def get_target(self):
        """Node name to use for this kind of remote execution."""
        target = None
        ntry = 0
        while target is None and ntry < self.maxtries:
            ntry += 1
            self._retries = ntry
            logger.debug('SSH connect try number ' + str(ntry))
            for guess in self.build_targets():
                try:
                    self.sh.spawn([
                        ' '.join((
                            self.sshcmd,
                            '-o', 'ConnectTimeout=1',
                            '-o', 'PasswordAuthentication=false',
                            guess,
                            'echo >/dev/null 2>&1'
                        ))],
                        shell  = True,
                        output = False,
                        silent = True,
                    )
                except StandardError:
                    pass
                else:
                    target = guess
                    break
        return target

    def __call__(self, *args):
        """Remote execution."""
        thistarget = self.get_target()
        if thistarget is None:
            logger.error('Could not find any valid SSH target in %s', str(self.build_targets()))
            rc = False
        else:
            logger.info('Remote command on target [%s] <%s>', thistarget, str(args))
            rc = self.sh.spawn(
                [ self.sshcmd ] + self.sshopts + [ thistarget ] + list(args),
                shell  = False,
                output = True,
            )
        return rc


class JeevesService(Service):
    """
    Class acting as a standard Bertie asking Jeeves to do something.
    """

    _footprint = dict(
        info = 'Jeeves services class',
        attr = dict(
            kind = dict(
                values   = ['askjeeves']
            ),
            todo = dict(),
            jname = dict(
                optional = True,
                default  = 'test',
            ),
            juser = dict(
                optional = True,
                default  = '[glove::user]',
            ),
            jpath = dict(
                optional = True,
                default  = None,
                access   = 'rwx',
            ),
            jfile = dict(
                optional = True,
                default  = 'vortex',
            ),
        )
    )

    def __call__(self, *args):
        """Main action: ..."""
        if self.jpath is None:
            self.jpath = self.sh.path.join(self.env.HOME, 'jeeves', self.jname, 'depot')
        if self.sh.path.isdir(self.jpath):
            from jeeves import bertie
            data = dict()
            for arg in args:
                data.update(arg)
            fulltalk = dict(
                user = self.juser,
                jtag = self.sh.path.join(self.jpath, self.jfile),
                todo = self.todo,
                mail = data.pop('mail', self.env.glove.email),
                apps = data.pop('apps', (self.env.glove.vapp,)),
                conf = data.pop('conf', (self.env.glove.vconf,)),
                task = self.env.get('JOBNAME') or self.env.get('SMSNAME', 'interactif'),
            )
            fulltalk.update(
                data = data,
            )
            jr = bertie.ask(**fulltalk)
            return (jr.todo, jr.last)
        else:
            logger.error('No valid path to jeeves <{!s}>'.format(self.jpath))
            return None


class HideService(Service):
    """
    Some service to hide data... for later use, perhaps...
    """

    _footprint = dict(
        info = 'Hide a given object on current filesystem',
        attr = dict(
            kind = dict(
                values   = ['hidden', 'hide', 'hiddencache'],
                remap    = dict(autoremap = 'first'),
            ),
            rootdir = dict(
                optional = True,
                default  = None,
            ),
            headdir = dict(
                optional = True,
                default  = 'tempo',
            ),
            asfmt = dict(
                optional = True,
                default  = None,
            ),
        )
    )

    def find_rootdir(self, filename):
        """Find a path for hidding files on the same filesystem."""
        username = self.sh.getlogname()
        fullpath = self.sh.path.realpath(filename)
        if username not in fullpath:
            logger.error('No login <%s> in path <%s>', username, fullpath)
            raise ValueError('Login name not in actual path for hidding data')
        return self.sh.path.join(fullpath.partition(username)[0], username, self.headdir)

    def __call__(self, *args):
        """Main action: ..."""
        for filename in args:
            actual_rootdir = self.rootdir or self.find_rootdir(filename)
            destination = self.sh.path.join(
                actual_rootdir,
                '.'.join((
                    'HIDDEN',
                    date.now().strftime('%Y%m%d%H%M%S.%f'),
                    'P{0:06d}'.format(self.sh.getpid()),
                    base64.b64encode(self.sh.path.abspath(filename))
                ))
            )
            self.sh.cp(filename, destination, intent='in', fmt=self.asfmt)
            return destination
