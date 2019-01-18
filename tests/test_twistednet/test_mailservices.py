# -*- coding: utf-8 -*-

'''
Test Vortex's Mailing Services
'''

from __future__ import print_function, absolute_import, unicode_literals, division

import base64
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
    ascii="""Content-Type: multipart/mixed; boundary="{boundary:s}"
MIME-Version: 1.0
From: test@unittest.dummy
To: queue
Subject: Test message (in english)

--{boundary:s}
Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

A very simple message.
--{boundary:s}
Content-Type: application/octet-stream
MIME-Version: 1.0
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="{fname:s}"

{b64:s}
--{boundary:s}--""",
    french="""Content-Type: multipart/mixed; boundary="{boundary:s}"
MIME-Version: 1.0
From: test@unittest.dummy
To: queue
Subject: =?utf-8?q?Message_de_test_=28en_Fran=C3=A7ais=29?=

--{boundary:s}
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable

Un message tr=C3=A8s simple.
--{boundary:s}
Content-Type: application/octet-stream
MIME-Version: 1.0
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="{fname:s}"

{b64:s}
--{boundary:s}--""",
)

_REF_TEMPLATED = """Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: quoted-printable
From: test@unittest.dummy
To: queue@unittest.dummy
Subject: =?utf-8?q?Some_extras_=28Toto=29_et_du_fran=C3=A7ais_emb=C3=AAtant?=


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
Subject: =?utf-8?q?Mail_with_xpid=3Dabcd_et_du_fran=C3=A7ais_emb=C3=AAtant?=

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

    def assertMessage(self, messages, ref, igalike=False):
        m = messages.get()
        m = [b.decode('ascii') for b in m]
        if igalike:
            m = [l for l in m
                 if not re.match(r'Mail envoy=C3=A9 le .* =C3=A0 .* locales.$', l)]
        head = "Received: MpQueueMessageDelivery\n"
        me = "\n".join(m)
        logger.info('Received:\n%s', me)
        logger.info('Expecting:\n%s', ref)
        self.assertEqual(me, head + ref)

    def assertMessagePlusAttach(self, messages, ref, filename, attached):
        m = messages.get()
        m = [b.decode('ascii') for b in m]
        if m[-2] == '':
            # Python2/Python3 difference but ok, it's equivalent
            del m[-2]
        b_m = re.match(r'Content-Type: multipart/mixed; boundary="([^"]+)"$', m[1])
        if b_m:
            boundary = b_m.group(1)
        else:
            self._raiseFailure("Malformed message.")
        attached_b64 = base64.b64encode(attached).decode('ascii')
        me = "\n".join(m)
        head = "Received: MpQueueMessageDelivery\n"
        logger.info('Received:\n%s', me)
        logger.info('Expecting:\n%s', ref.format(boundary=boundary, fname=filename,
                                                 b64=attached_b64))
        self.assertEqual(me, head + ref.format(boundary=boundary, fname=filename,
                                               b64=attached_b64))

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
                    self.assertMessagePlusAttach(messages, _REFS2[testid],
                                                 tmpfh.name, _BYTES2ATTACH)
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
