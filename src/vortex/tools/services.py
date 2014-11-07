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

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import sessions

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

    def __call__(self):
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
                alias    = ('receiver', 'recipients')
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
            server = dict(
                optional = True,
                default  = 'localhost',
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

    def get_message_body(self):
        """Returns the internal body contents as a MIMEText object."""
        body = self.message
        if self.filename:
            with open(self.filename, 'r') as tmp:
                body += tmp.read()
        mimetext = self.get_mimemap().get('text')
        return mimetext(body)

    def get_mimemap(self):
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
        msg['To'] = self.commaspace.join(self.to.split())
        msg['Subject'] = self.subject

    def __call__(self):
        """Main action: pack the message body, add the attachments, and send via SMTP."""
        import smtplib
        msg = self.get_message_body()
        if self.attachments:
            msg = self.as_multipart(msg)
        self.set_headers(msg)
        msgcorpus = msg.as_string()
        smtp = smtplib.SMTP(self.server)
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

    def __call__(self):
        """Main action: ..."""
        pass


class FileReportService(ReportService):
    """Building the report as a simple file."""

    _footprint = dict(
        info = 'File Report services class',
        attr = dict(
            kind = dict(
                values   = ['sendfilereport']
            ),
            file = dict(
                default  = 'info'
            )
        )
    )


