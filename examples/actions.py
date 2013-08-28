#!/bin/env python
# -*- coding:Utf-8 -*-

# Status : OK (v0.6.20)

import vortex

from vortex.tools.actions import actiond as ad
from vortex.tools.actions import SendMail

class TagSubject(SendMail):

    def __init__(self, tag='DEBUG'):
        self.tag = tag
        super(TagSubject, self).__init__()

    def service_info(self, **kw):
        kw['subject'] = self.tag + ': ' + kw.get('subject', 'no subject')
        return super(TagSubject, self).service_info(**kw)

ad.add(TagSubject())

print ad.actions()
print ad.candidates('mail')

g = vortex.sessions.glove()
g.setmail('eric.sevault@meteo.fr')

ad.mail(to='eric.sevault@meteo.fr', subject='hello', body='hello world mail')
