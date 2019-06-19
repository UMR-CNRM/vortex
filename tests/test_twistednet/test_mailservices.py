# -*- coding: utf-8 -*-

"""
Test Vortex's Mailing Services
"""

from __future__ import print_function, absolute_import, unicode_literals, division
import six

import base64
import email
from email import parser as eparser
import functools
import os
import re
import tempfile
import unittest

from bronx.fancies import loggers
from footprints import proxy as fpx

import vortex
from vortex import sessions
import vortex.tools.services  # @UnusedImport
import iga.tools.services  # @UnusedImport
from vortex.tools.services import Directory
from vortex.util.config import GenericConfigParser

from . import has_mailservers
from .utils import get_email_port_number

tloglevel = 9999

logger = loggers.getLogger(__name__)

_MSGS = dict(
    ascii='A very simple message.',
    french='Un message très simple.',
)

_SUBJECTS = dict(
    ascii='Test message (in english)',
    french='Message de test (en Français)',
)

_REFS = dict(
    ascii="""Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
From: test@unittest.dummy
To: queue
Subject: Test message (in english)

A very simple message.""",
    french="""Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable
From: test@unittest.dummy
To: queue
Subject: =?utf-8?q?Message_de_test_=28en_Fran=C3=A7ais=29?=

Un message tr=C3=A8s simple.""",
)

_REFS2 = dict(
    ascii="""Content-Type: multipart/mixed; boundary="dfgqfgqf5687241=="
MIME-Version: 1.0
From: test@unittest.dummy
To: queue
Subject: Test message (in english)

--dfgqfgqf5687241==
Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

A very simple message.
--dfgqfgqf5687241==
Content-Type: application/octet-stream
MIME-Version: 1.0
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="{fname:s}"

{b64:s}
--dfgqfgqf5687241==--""",
    french="""Content-Type: multipart/mixed; boundary="dfgqfgqf5687241=="
MIME-Version: 1.0
From: test@unittest.dummy
To: queue
Subject: =?utf-8?q?Message_de_test_=28en_Fran=C3=A7ais=29?=

--dfgqfgqf5687241==
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable

Un message tr=C3=A8s simple.
--dfgqfgqf5687241==
Content-Type: application/octet-stream
MIME-Version: 1.0
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="{fname:s}"

{b64:s}
--dfgqfgqf5687241==--""",
)

_REF_TEMPLATED = """Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable
From: test@unittest.dummy
To: queue@unittest.dummy
Subject: =?utf-8?q?Some_extras_=28Toto=29_et_du_fran=C3=A7ais_emb=C3=AAta?=
 =?utf-8?q?nt?=


Variable prise dans env  : op_suite =3D oper
Variable prise en add_on : extra    =3D Toto
Variable manquante       : missing  =3D $missing
Syntaxe ill=C3=A9gale         : op_suite =3D $(op_suite)

Substitution:
   $op_suite         =3D oper
   ${op_suite}       =3D oper
   test_$op_suite    =3D test_oper
   test_$op_suite@mf =3D test_oper@mf

Accents:
   Portez ce vieux whisky au juge blond qui fume : d=C3=A8s No=C3=ABl o=C3=
=B9
   un z=C3=A9phyr ha=C3=AF le v=C3=AAt de gla=C3=A7ons w=C3=BCrmiens il d=
=C3=AEne =C3=A0 s'emplir
   le c=C3=A6cum d=E2=80=99exquis r=C3=B4tis de b=C5=93uf =C3=A0 l=E2=80=99=
a=C3=BF d=E2=80=99=C3=A2ge m=C3=BBr et s'=C3=A9crie
   "=C3=80 =C3=82 =C3=89 =C3=88 =C3=8A =C3=8B =C3=8E =C3=8F =C3=94 =C3=99 =
=C3=9B =C3=9C =C3=87 =C5=92 =C3=86" !"""

_REF_IGA = """Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable
From: test@unittest.dummy
To: queue@unittest.dummy
Subject: =?utf-8?q?Mail_with_xpid=3Dabcd_et_du_fran=C3=A7ais_emb=C3=AAtan?=
 =?utf-8?q?t?=

--


Variable prise dans env  : op_suite =3D oper
Variable prise en add_on : extra    =3D some extra
Variable manquante       : missing  =3D $missing
Syntaxe ill=C3=A9gale         : op_suite =3D $(op_suite)

Substitution:
   $op_suite         =3D oper
   ${{op_suite}}       =3D oper
   test_$op_suite    =3D test_oper
   test_$op_suite@mf =3D test_oper@mf

Accents:
   Portez ce vieux whisky au juge blond qui fume : d=C3=A8s No=C3=ABl o=C3=
=B9
   un z=C3=A9phyr ha=C3=AF le v=C3=AAt de gla=C3=A7ons w=C3=BCrmiens il d=
=C3=AEne =C3=A0 s'emplir
   le c=C3=A6cum d=E2=80=99exquis r=C3=B4tis de b=C5=93uf =C3=A0 l=E2=80=99=
a=C3=BF d=E2=80=99=C3=A2ge m=C3=BBr et s'=C3=A9crie
   "=C3=80 =C3=82 =C3=89 =C3=88 =C3=8A =C3=8B =C3=8E =C3=8F =C3=94 =C3=99 =
=C3=9B =C3=9C =C3=87 =C5=92 =C3=86" !

--
Envoi automatique par Vortex {vversion:s} pour <tourist@unittest>."""

_INPUTMSG_ENCODING = 'utf-16'

_BYTES2ATTACH = "AZERTYbutéàù%".encode('utf-8')

_DATAPATHTEST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    'data')


@unittest.skipUnless(has_mailservers(), 'Mail Server')
@loggers.unittestGlobalLevel(tloglevel)
class TestEmailServices(unittest.TestCase):

    def setUp(self):
        # Configure session : it is relatively useless but using
        # 'target-test.ini' and hostname='unittestlogin001', we are guaranteed
        # that the mail service will attempt to contact the SMTP server
        self.testconf = os.path.join(_DATAPATHTEST, 'target-test.ini')
        self._oldsession = sessions.current()
        gl = sessions.getglove(profile='oper', user='mxpt001')
        ns = sessions.get(tag='mails_unittest_view',
                          topenv=vortex.rootenv, glove=gl)
        ns.activate()
        ns.sh.target(hostname='unittestlogin001', inetname='unittest',
                     sysname='Linux', inifile=self.testconf)
        self.env = ns.env
        # Configure mail stuff
        self.port = get_email_port_number()
        self.configure_mailserver()
        self.servicedefaults = dict(
            smtpserver = 'localhost',
            smtpport = self.port,
            sender = 'test@unittest.dummy',
        )

    def tearDown(self):
        self._oldsession.activate()

    def configure_mailserver(self):
        from .mailservers import TestMailServer, logger
        logger.setLevel(tloglevel)
        self.server = TestMailServer(self.port)

    def _parse_messages(self, ref, messages, **kwargs):
        mparser = (eparser.FeedParser if six.PY2 else
                   functools.partial(eparser.BytesFeedParser,
                                     email.message.EmailMessage,
                                     policy=email.policy.strict))
        # Ref message
        p_ref = mparser()
        p_ref.feed(b'Received: MpQueueMessageDelivery\n')
        p_ref.feed((ref.format(**kwargs) if kwargs else ref).encode('ascii'))
        m_ref = p_ref.close()
        # New message
        m = messages.get()
        p_new = mparser()
        p_new.feed(b'\n'.join(m))
        m_new = p_new.close()
        return m_ref, m_new

    def assertMessage(self, messages, ref, igalike=False):
        m_ref, m_new = self._parse_messages(ref, messages)
        # Compare headers
        h_ref = dict(m_ref.items())
        h_new = dict(m_new.items())
        self.assertDictEqual(h_ref, h_new)
        # Compare bodies
        if not m_new.is_multipart():
            if six.PY2:
                b_ref = m_ref.get_payload(decode=True)
                b_ref = b_ref.decode(m_ref.get_content_charset('ascii'))
                b_new = m_new.get_payload(decode=True)
                b_new = b_new.decode(m_new.get_content_charset('ascii'))
            else:
                b_ref = m_ref.get_body().get_content()
                b_new = m_new.get_body().get_content()
            if igalike:
                b_new = '\n'.join([l for l in b_new.split('\n')
                                   if not re.match('Mail envoyé le .* à .* locales.$', l)])
            logger.info('Received:\n%s', b_ref)
            logger.info('Expecting:\n%s', b_new)
            self.assertEqual(b_ref, b_new)
        else:
            raise RuntimeError("This test is ill-designed: no multipart messages allowed here.")

    def assertMessagePlusAttach(self, messages, ref, filename, attached):
        attached_b64 = base64.b64encode(attached).decode('ascii')
        m_ref, m_new = self._parse_messages(ref, messages,
                                            fname=filename, b64=attached_b64)
        # Compare bodies
        if m_new.is_multipart():
            b_ref = [(b_item.get_payload(decode=False).decode(b_item.get_content_charset('ascii'))
                      if six.PY2 else b_item.get_content())
                     for b_item in m_ref.walk() if not b_item.is_multipart()]
            b_new = [(b_item.get_payload(decode=False).decode(b_item.get_content_charset('ascii'))
                      if six.PY2 else b_item.get_content())
                     for b_item in m_new.walk() if not b_item.is_multipart()]
            for a_ref, a_new in zip(b_ref, b_new):
                logger.info('Received:\n%s', a_ref)
                logger.info('Expecting:\n%s', a_new)
                if isinstance(a_ref, six.string_types):
                    self.assertEqual(a_ref.rstrip('\n'), a_new.rstrip('\n'))
                else:
                    self.assertEqual(a_ref, a_new)
        else:
            raise RuntimeError("This test is ill-designed: no multipart messages allowed here.")
        # Compare headers
        m_ref.set_boundary(m_new.get_boundary())  # The boundary allows changes
        h_ref = dict(m_ref.items())
        h_new = dict(m_new.items())
        self.assertDictEqual(h_ref, h_new)

    def test_email_service(self):
        with self.server() as messages:
            for testid in ('ascii', 'french'):
                eserv = fpx.service(kind="sendmail",
                                    message = _MSGS[testid],
                                    subject = _SUBJECTS[testid],
                                    to = 'queue',
                                    ** self.servicedefaults)
                eserv()
                self.assertMessage(messages, _REFS[testid])
                # Read the message body from a file
                with tempfile.NamedTemporaryFile(prefix='test_mailservices_', mode='wb') as tmpfh:
                    tmpfh.write(_MSGS[testid].encode(_INPUTMSG_ENCODING))
                    tmpfh.flush()
                    eserv = fpx.service(kind="sendmail",
                                        filename = tmpfh.name,
                                        inputs_charset = _INPUTMSG_ENCODING,
                                        subject = _SUBJECTS[testid],
                                        to = 'queue',
                                        ** self.servicedefaults)
                    eserv()
                    self.assertMessage(messages, _REFS[testid])
                # With an attachment
                with tempfile.NamedTemporaryFile(prefix='test_mailservices_', mode='wb') as tmpfh:
                    tmpfh.write(_BYTES2ATTACH)
                    tmpfh.flush()
                    eserv = fpx.service(kind="sendmail",
                                        message = _MSGS[testid],
                                        subject = _SUBJECTS[testid],
                                        attachments = [tmpfh.name, ],
                                        to = 'queue',
                                        ** self.servicedefaults)
                    eserv()
                    self.assertMessagePlusAttach(messages, _REFS2[testid], tmpfh.name, _BYTES2ATTACH)
            # Templated Mails
            eserv = fpx.service(kind="templatedmail",
                                id="test_base",
                                directory=Directory(os.path.join(_DATAPATHTEST,
                                                                 'mailtest_addressbook.ini'),
                                                    encoding='utf-8'),
                                catalog=GenericConfigParser(inifile=os.path.join(_DATAPATHTEST,
                                                                                 'mailtest_inventory.ini'),
                                                            encoding='utf-8'),
                                inputs_charset = 'utf-8',
                                ** self.servicedefaults)
            with self.env.clone() as tenv:
                tenv.OP_SUITE = 'oper'
                eserv(dict(extra='Toto'))
            self.assertMessage(messages, _REF_TEMPLATED)
            # OpMails
            eserv = fpx.service(kind="opmail",
                                id="test",
                                directory=Directory(os.path.join(_DATAPATHTEST,
                                                                 'mailtest_addressbook.ini'),
                                                    encoding='utf-8'),
                                catalog=GenericConfigParser(inifile=os.path.join(_DATAPATHTEST,
                                                                                 'mailtest_inventory.ini'),
                                                            encoding='utf-8'),
                                inputs_charset = 'utf-8',
                                ** self.servicedefaults)
            with self.env.clone() as tenv:
                tenv.OP_SUITE = 'oper'
                tenv.OP_XPID = 'ABCD'
                tenv.user = 'tourist'
                eserv(dict(extra='some extra'))
            self.assertMessage(messages, _REF_IGA.format(vversion=vortex.__version__),
                               igalike=True)
