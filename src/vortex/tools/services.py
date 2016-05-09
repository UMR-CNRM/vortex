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
from string import Template
from ConfigParser import NoOptionError, NoSectionError

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import sessions
from vortex.tools import date

from vortex.tools.actions import actiond as ad
from vortex.util.config import GenericConfigParser, load_template
from vortex.util.structs import Utf8PrettyPrinter


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
        """Return True if any character in string is not ascii-7."""
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
        msg['From'] = self.sender
        msg['To']   = self.commaspace.join(self.to.split())
        if self.is_not_plain_ascii(self.subject):
            from email.header import Header
            msg['Subject'] = Header(self.subject, self.charset)
        else:
            msg['Subject'] = self.subject

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
    """Remote execution via ssh on a generic target.

    If ``node`` is the specified :attr:`hostname` value, some target hostname
    will be built on the basis of attributes, :attr:`genericnode`,
    :attr:`nodebase`, :attr:`nodetype` and :attr:`noderange`.

    In this case, if :attr:`genericnode` is defined it will be used. If not, the
    configuration file will be checked for a configuration key named
    ``'{}node'.format(self.nodetype)`` in the services section.

    If none of the :attr:`genericnode` attribute or its configuration file
    counterpart is defined, then ``hostname = self.nodebase + self.nodetype + nodenumber``.
    When several ``nodenumber`` are available (they are values of the
    :attr:`noderange` attribute with random permutation or not), the first
    responding ``hostname`` will be selected.
    """

    _footprint = dict(
        info = 'Remote command proxy',
        attr = dict(
            kind = dict(
                values   = ['ssh', 'ssh_proxy'],
                remap    = dict(autoremap = 'first'),
            ),
            hostname = dict(),
            genericnode = dict(
                optional = True,
                default  = None,
                access   = 'rwx',
            ),
            nodebase = dict(
                optional = True,
                default  = None,
                access   = 'rwx',
            ),
            nodetype = dict(
                optional = True,
                values   = ['login', 'transfer'],
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
                default  = None,
            ),
            sshopts = dict(
                optional = True,
                type     = footprints.FPList,
                default  = None,
            ),
            sshretryopts = dict(
                optional = True,
                type     = footprints.FPList,
                default  = None,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Remote command proxy init %s', self.__class__)
        super(SSHProxy, self).__init__(*args, **kw)
        self._retries = None

    def _actual_sshopts(self, key):
        act = self.actual_value(key)
        if not isinstance(act, (list, tuple)):
            act = act.split()
        return act

    @property
    def retries(self):
        return self._retries

    def _build_targets(self):
        """Build a list of candidate target hostnames."""
        targets = [ self.hostname.strip().lower() ]
        if targets[0] == 'node':
            genericnode = self.genericnode or self.actual_value(self.nodetype + 'node',)
            if genericnode and genericnode != 'no_generic':
                targets = [ genericnode, ]
            else:
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

    def _get_target(self, targets):
        """Node name to use for this kind of remote execution."""
        target = None
        ntry = 0
        while target is None and ntry < self.maxtries:
            ntry += 1
            self._retries = ntry
            logger.debug('SSH connect try number ' + str(ntry))
            for guess in targets:
                try:
                    thecmd = [' '.join([ self.actual_value('sshcmd'), ] +
                                       self._actual_sshopts('sshopts') +
                                       self._actual_sshopts('sshretryopts') +
                                       [ guess, 'echo >/dev/null 2>&1'])]
                    self.sh.spawn(thecmd, shell=True, output=False, silent=True)
                except StandardError:
                    pass
                else:
                    target = guess
                    break
        return target

    def __call__(self, *args):
        """Remote execution."""
        targets = self._build_targets()
        if len(targets) > 1:
            thistarget = self._get_target(targets)
            if thistarget is None:
                logger.error('Could not find any valid SSH target in %s', str(targets))
                return False
        else:
            thistarget = targets[0]

        logger.info('Remote command on target [%s] <%s>', targets[0], str(args))
        thecmd = [ self.actual_value('sshcmd') ] + self._actual_sshopts('sshopts') + [ thistarget ] + list(args)
        return self.sh.spawn(thecmd, shell=False, output=True)


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


class Directory(object):
    """
    A class to represent and use mail aliases.

    Directory (en) means Annuaire (fr).
    """

    def __init__(self, inifile, domain='meteo.fr'):
        """Keep aliases in memory, as a dict of sets."""
        config = GenericConfigParser(inifile)
        try:
            self.domain = config.get('general', 'default_domain')
        except NoOptionError:
            self.domain = domain
        self.aliases = {
            k.lower(): set(v.lower().replace(',', ' ').split())
            for (k, v) in config.items('aliases')
        }
        count = self._flatten()
        logger.debug('opmail aliases flattened in {} iterations:\n{}'.format(count, self))

    def get_addresses(self, definition, add_domain=True):
        """Build a space separated list of unique mail addresses
           from a string that may reference aliases."""
        addresses = set()
        for item in definition.replace(',', ' ').split():
            if item in self.aliases:
                addresses |= self.aliases[item]
            else:
                addresses |= {item}
        if add_domain:
            return ' '.join(self._add_domain(addresses))
        return ' '.join(addresses)

    def __str__(self):
        return '\n'.join(sorted(
            ['{}: {}'.format(k, ' '.join(sorted(v)))
             for (k, v) in self.aliases.iteritems()]
        ))

    def _flatten(self):
        """Resolve recursive definitions from the dict of sets."""
        changed = True
        count = 0
        while changed:
            changed = False
            count += 1
            for kref, vref in self.aliases.iteritems():
                if kref in vref:
                    logger.error('Cycle detected in the aliases directory.\n'
                                 'offending key: {}.\n'
                                 'directory being flattened:\n{}'.format(kref,self))
                    raise ValueError('Cycle for key <{}> in directory definition'.format(kref))
                for k, v in self.aliases.iteritems():
                    if kref in v:
                        v -= {kref}
                        v |= vref
                        self.aliases[k] = v
                        changed = True
        return count

    def _add_domain(self, aset):
        """Add domain where missing in a set of addresses."""
        return {
            v if '@' in v
            else v + '@' + self.domain
            for v in aset
        }


class PromptService(Service):
    """
    Class used to simulate a real Service: logs the argument it receives.
    This class should not be called directly.
    """

    _footprint = dict(
        info = 'Simulate a call to a Service.',
        attr = dict(
            kind = dict(
                values   = ('prompt',),
            ),
            comment = dict(
                optional = True,
                default  = None,
            ),
        )
    )

    def __call__(self, options):
        """Prints what arguments the action was called with."""
        pf = Utf8PrettyPrinter().pformat
        logger_action = getattr(logger, self.level, logger.warning)
        msg = (self.comment or 'PromptService was called.') + '\noptions = {}'
        logger_action (msg.format(pf(options)).replace('\n', '\n<prompt> '))
        return True


class TemplatedMailService(MailService):
    """
    Class responsible for sending templated mails.
    This class should not be called directly.
    """

    _footprint = dict(
        info = 'Templated mail services class',
        attr = dict(
            kind = dict(
                values   = ['templatedmail'],
            ),
            id = dict(
                alias    = ('template',),
            ),
            subject = dict(
                optional = True,
                default  = None,
                access   = 'rwx',
            ),
            to = dict(
                optional = True,
                default  = None,
                access   = 'rwx',
            ),
            message = dict(
                access   = 'rwx',
            ),
            directory = dict(
                type     = Directory,
                optional = True,
                default  = None,
            ),
            catalog = dict(
                type     = GenericConfigParser,
            ),
        )
    )

    def __init__(self, *args, **kw):
        ticket = kw.pop('ticket', sessions.get())
        super(TemplatedMailService, self).__init__(*args, **kw)
        self._ticket = ticket
        logger.debug('TemplatedMail init for id <{}>'.format(self.id))

    @property
    def ticket(self):
        return self._ticket

    def header(self):
        """String prepended to the message body."""
        return ''

    def trailer(self):
        """String appended to the message body."""
        return ''

    def deactivated(self):
        """Return True to eventually prevent the mail from being sent."""
        return False

    def get_catalog_section(self):
        """Read section <id> (a dict-like) from the catalog."""
        try:
            section = dict(self.catalog.items(self.id))
        except NoSectionError:
            logger.error('Section <{}> is missing in catalog <{}>'.format(self.id, self.catalog.file))
            section = None
        return section

    def substitution_dictionary(self, add_ons=None):
        """Dictionary used for template substitutions: env + add_ons."""
        dico = footprints.util.UpperCaseDict(self.env)
        if add_ons is not None:
            dico.update(add_ons)
        return dico

    @staticmethod
    def substitute(tpl, tpldict, depth=1):
        """Safely apply template substitution.

          * Syntactic and missing keys errors are detected and logged.
          * on error, a safe substitution is applied.
          * The substitution is iterated ``depth`` times.
        """
        if not isinstance (tpl, Template):
            tpl = Template(tpl)
        result = ''
        for level in range(depth):
            try:
                result = tpl.substitute(tpldict)
            except KeyError as exc:
                logger.error('Undefined key <{}> in template substitution level {}'.format(exc.message, level+1))
                result = tpl.safe_substitute(tpldict)
            except ValueError as exc:
                logger.error('Illegal syntax in template: {}'.format(exc.message))
                result = tpl.safe_substitute(tpldict)
            tpl = Template(result)
        return result

    def get_message(self, tpldict):
        """Contents:

          * from the fp if given, else the catalog gives the template file name.
          * template-substituted.
          * header and trailer are added.
        """
        tpl = self.message
        if tpl == '':
            tplfile = self.section.get('template', self.id)
            if not tplfile.startswith('opmail-'):
                tplfile = 'opmail-' + tplfile
            if not tplfile.endswith('.tpl'):
                tplfile += '.tpl'
            try:
                tpl = load_template(self.ticket, tplfile)
            except ValueError as exc:
                logger.error('{}'.format(exc.message))
                return None
        message = self.substitute(tpl, tpldict)
        return self.header() + message + self.trailer()

    def get_subject(self, tpldict):
        """Subject:

          * from the fp if given, else from the catalog.
          * template-substituted.
        """
        tpl = self.subject
        if tpl is None:
            tpl = self.section.get('subject', None)
            if tpl is None:
                logger.error('Missing <subject> definition for id <{}>.'.format(self.id))
                return None
        subject = self.substitute(tpl, tpldict)
        return subject

    def get_to(self, tpldict):
        """Recipients:

          * from the fp if given, else from the catalog.
          * template-substituted.
          * expanded by the directory (if any).
          * substituted again, to allow for $vars in the directory.
          * directory-expanded again for domain completion and unicity.
        """
        tpl = self.to
        if tpl is None:
            tpl = self.section.get('to', None)
            if tpl is None:
                logger.error('Missing <to> definition for id <{}>.'.format(self.id))
                return None
        to = self.substitute(tpl, tpldict)
        if self.directory:
            to = self.directory.get_addresses(to, add_domain=False)
        # substitute again for directory definitions
        to = self.substitute(to, tpldict)
        # last resolution, plus add domain and remove duplicates
        if self.directory:
            to = self.directory.get_addresses(to)
        return to

    def prepare(self, add_ons=None):
        """Prepare elements in turn, return True iff all succeeded."""
        self.section = self.get_catalog_section()
        if self.section is None:
            return False

        tpldict = self.substitution_dictionary(add_ons)

        self.message = self.get_message(tpldict)
        if self.message is None:
            return False

        self.subject = self.get_subject(tpldict)
        if self.subject is None:
            return False

        self.to = self.get_to(tpldict)
        if self.to is None:
            return False

        return True

    def __call__(self, *args):
        """Main action:

          * substitute templates where needed.
          * apply directory definitions to recipients.
          * activation is checked before sending via the Mail Service.

        Arguments are passed as add_ons to the substitution dictionary.
        """
        add_ons =dict()
        for arg in args:
            add_ons.update(arg)
        rc = False
        if self.prepare(add_ons) and not self.deactivated():
            rc = super(TemplatedMailService, self).__call__()
        return rc
