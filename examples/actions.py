#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex.tools.actions import actiond as ad
from vortex.tools.actions import SendMail

print ad.actions()

class TagSubject(SendMail):

    def __init__(self, tag='DEBUG'):
        self.tag = tag
        super(TagSubject, self).__init__()

    def service_info(self, **kw):
        kw['Subject'] = self.tag + ': ' + kw.get('Subject', 'no subject')       
        return super(TagSubject, self).service_info(**kw)

ad.add(TagSubject())
print ad.actions()
print ad.candidates('mail')
