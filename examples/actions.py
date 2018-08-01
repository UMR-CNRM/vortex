#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This example aims at sending an email to a specified user.
The variable my_email must be changed, otherwise it won't work.

The commented part can be used to transform the mail service to send an other mail at each mail sent.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import vortex

from vortex.tools.actions import actiond as ad
#from vortex.tools.actions import SendMail


#
my_email = "gaelle.rigoudy@meteo.fr"

# # Part which is used to change the mail service, can be uncommented
# class TagSubject(SendMail):
#
#     def __init__(self, tag='DEBUG'):
#         self.tag = tag
#         super(TagSubject, self).__init__()
#
#     def service_info(self, **kw):
#         kw['subject'] = self.tag + ': ' + kw.get('subject', 'no subject')
#         return super(TagSubject, self).service_info(**kw)
#
# ad.add(TagSubject())

# Try to figure out which actions are available
print(ad.actions)
print(ad.candidates('mail'))

# Configure the glove
g = vortex.sessions.getglove()
g.email = my_email

# Try to send an e-mail
ad.mail(to=my_email, subject='hello', body='hello world mail')
