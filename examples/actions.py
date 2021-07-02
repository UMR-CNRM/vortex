#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This example shows how to send an email to a specified user.
The variable 'my_email' must be changed for this example to work.

The optional part (see 'add_an_action') defines an Action able to respond to
'mail' requests, and adds it to the Actions handling mechanism. A subsequent
mail request is handled both by the standard 'SendMail' installed by default
in Vortex, and by this user-defined Action. In this simple example, the mail
is just sent with 'DEBUG: ' prepended to the subject.

Ok 20180802 - PL
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import vortex
from vortex.tools.actions import actiond as ad

add_an_action = True

if add_an_action:
    from vortex.tools.actions import SendMail


    class TagSubject(SendMail):

        def __init__(self, tag='DEBUG'):
            self.tag = tag
            super(TagSubject, self).__init__()

        def service_info(self, **kw):
            kw['subject'] = self.tag + ': ' + kw.get('subject', 'no subject')
            return super(TagSubject, self).service_info(**kw)


    ad.add(TagSubject())

# change this to your email address
# my_email = "gaelle.rigoudy@meteo.fr"
# my_email = "pascal.lamboley@meteo.fr"
my_email = "firstname.lastname@meteo.fr"

# show all available actions
print(ad.actions)

# show what actions respond to a 'mail' request
print(ad.candidates('mail'))

# Configure the glove
g = vortex.sessions.getglove()
g.email = my_email

# Try to send an e-mail
ad.mail(to=my_email, subject='hello', body='hello world mail')
