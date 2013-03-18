.. _actions-usage:

********************
Actions and Services
********************

Actions could be seen as some external tools, not deeply tied up with the toolbox itself,
or at least not diretly related to NWP stuff.
Typical actions could consist in sending a mail, issuing an alarm
or producing some kind of execution report.

The action is directly what you want to do, while the service is much more what make it possible.

============================
Using the actions dispatcher
============================

Even if actions and services could be directly manipulated, it could be of some convenience
to go through an Actions Dispatcher. A default one arrives with the :mod:`vortex.tools.actions` module.
This kind of dispatcher is in fact a very simple catalog:

.. code-block:: python

  >>> from vortex.tools.actions import actiond as ad
  >>> ad
  <vortex.tools.actions.Dispatcher object at 0x2471450>
  >>> ad.items()
  [<vortex.tools.actions.SendMail object at 0x2471590>]
  >>> ad.actions()
  set(['mail'])

Modules that implement actions should register to this default actions dispatcher,
in order to be globaly accessible:

.. code-block:: python

  >>> from vortex.tools.actions import actiond as ad
  >>> ad.actions()
  set(['mail'])
  >>> import iga.tools.actions
  >>> ad.actions()
  set(['mail', 'alarm', 'agt'])

If we have a look to this :mod:`iga.tools.actions` for exemple, we can see the registering operation
at the import time:

.. code-block:: python

  from vortex.tools.actions import Action, actiond

  class SendAlarm(Action):
    def __init__(self, kind='alarm'):
      super(SendAlarm, self).__init__(kind)


  class SendAgt(Action):
    def __init__(self, kind='agt', service='routing'):
      super(SendAgt, self).__init__(kind)

  actiond.add(SendAlarm(), SendAgt())

Using a dispatcher, actions are collectively performed according to the ``kind`` of the action.
It means, that several actions could be candidates for a given value of ``kind``. Here is an
exemple whith a second mail action:

.. code-block:: python

  >>> from vortex.tools.actions import actiond as ad
  >>> from vortex.tools.actions import SendMail
  >>> ad.actions()
  set(['mail'])
  >>> class TagSubject(SendMail):
  ...   def __init__(self, tag='DEBUG'):
  ...     self.tag = tag
  ...     super(TagSubject, self).__init__()
  ...   def service_info(self, **kw):
  ...     kw['Subject'] = self.tag + ': ' + kw.get('Subject', 'no subject')
  ...     return super(TagSubject, self).service_info(**kw)
  >>> ad.add(TagSubject())
  >>> print ad.actions()
  set(['mail'])
  >>> print ad.candidates('mail')
  [<vortex.tools.actions.SendMail object at 0x1d5f410>, <__main__.TagSubject object at 0x1d5f450>]

Some other global operations involves switching status of actions.
For exemple, if we continue with the case of two objects related to a ``mail`` action:

.. code-block:: python

  >>> print ad.candidates('mail')
  [<__main__.TagSubject object at 0x2928710>, <vortex.tools.actions.SendMail object at 0x29285d0>]
  >>> ad.mail_status()
  [True, True]
  >>> ad.mail_off()
  [False, False]


=======
Actions
=======

An action derives from the :class:`vortex.tools.actions.Action` class. It could be active or not.

.. code-block:: python

  >>> from vortex.tools.actions import SendMail
  >>> sm = SendMail()
  >>> sm.active
  True
  >>> sm.off()
  False
  >>> sm.active
  False

========
Services
========

A service derives from a :class:`~vortex.syntax.footprint.BFootprint` base class.
Root class and usual module interface for such object is available
through the :mod:`vortex.tools.services` module.

.. code-block:: python

  >>>

