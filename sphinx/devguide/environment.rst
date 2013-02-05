.. _env-interface:

**********************************   
Understanding environment features
**********************************


What could be defined as a full featured environment is the combination
of three classes of objects :

* a vortex session :class:`vortex.sessions.Ticket`,
* a global verstatile environment :class:`vortex.gloves.Glove`,
* an active environment binded to operating system :class:`vortex.tools.env.Environment`.

A session Ticket is always binded to a root environment (the one the session was started in),
and each Environment is populated with a Glove. Whether this ticket or environment remains
active, and what "active" means, is an other matter and depends of the current usage.
For the time being, let say that at any time during a vortex experiment, one could
be aware of the current session and current active environment in relation to the current
global versatile environment.


================
Default Behavior
================

Let's start with the default behavior, assuming that the user does not want yet
to hack things behind the scene.

The top level import
====================

At the very begining, as soon as the import of the :mod:`vortex` module is done,
a :envvar:`rootenv` is defined. It remains directly accessible at any
time and should not be changed. It is the actual os environment at launch time.

.. code-block:: python

  >>> import vortex
  >>> vortex.rootenv
  <vortex.tools.env.Environment object at 0x1284ad0>

This environment is given a default glove, such as the one that results from
a empty load without any specific description whatsoever.

.. code-block:: python

  >>> vortex.rootenv.glove
  <vortex.gloves.ResearchGlove object at 0x1275bd0>


A default session ticket is also defined, that could be retrieved through the :func:`ticket` method:

.. code-block:: python

  >>> vortex.ticket()
  <vortex.sessions.Ticket object at 0x127ab90>

The environment attached to this session is derivated from the :envvar:`rootenv` contents but is not the same
object:

.. code-block:: python

  >>> vortex.rootenv
  <vortex.tools.env.Environment object at 0x1284ad0>
  >>>
  >>> s = vortex.ticket()
  >>> s.env
  <vortex.tools.env.Environment object at 0x127ac50>
  >>> s.topenv
  <vortex.tools.env.Environment object at 0x1284ad0>

Therefore, if we ask to the :mod:`vortex.tools.env` module which environment is the current one,
it is this last one who is active, note the :envvar:`rootenv`:

.. code-block:: python

  >>> vortex.tools.env.current()
  <vortex.tools.env.Environment object at 0x127ac50>

But the default glove in the default session is really the one automatically defined at the import time:

.. code-block:: python

  vortex.rootenv.glove
  <vortex.gloves.ResearchGlove object at 0x1275bd0>
  >>> s.glove
  <vortex.gloves.ResearchGlove object at 0x1275bd0>

The init vortex module
======================

Let's have a look to the init module itself, in order to completly understand this mechanism:

.. code-block:: python

  import sessions, algo, data
  import tools

  rootenv = tools.env.Environment(active=True)
  rootenv.glove = sessions.glove()

  sessions.ticket(topenv=rootenv, glove=rootenv.glove, prompt='Vortex v-'+__version__+':')

  def ticket():
    return sessions.ticket()

  def sh():
    return sessions.system()

We can verify that the :envvar:`rootenv` is used as the top environment for
the default session creation.

===============
Vortex sessions
===============

Using most of the Vortex toolbox features could be achieved through the root session defined at import time.
Nevertheless, the user or the developper could easily beneficiate from advanced features defined in the module
:mod:`vortex.sessions`.

Creating a new session
======================

New sessions should only be defined through the interface function :func:`vortex.sessions.ticket`.
The function :func:`vortex.ticket` is a shortcut to this function.

If no ``tag`` argument is provided, or if tag is set to ``current``, the current active session is returned:

.. code-block:: python

  >>> import vortex
  >>> vortex.ticket()
  <vortex.sessions.Ticket object at 0x101ec50>
  >>> vortex.ticket(tag='current')
  <vortex.sessions.Ticket object at 0x101ec50>
  >>> vortex.ticket(tag='root')
  <vortex.sessions.Ticket object at 0x101ec50>

Current defined sessions tags names could be retrieved through the function :func:`vortex.sessions.sessionstags`:

.. code-block:: python

  >>> from vortex import sessions
  >>> sessions.sessionstags()
  ['root']

As soon as a non-existent ``tag`` is provided, a new ticket session is returned:

.. code-block:: python

  sessions.ticket()
  <vortex.sessions.Ticket object at 0x101ec50>
  >>> sessions.ticket(tag='foo')
  <vortex.sessions.Ticket object at 0x10278d0>
  >>> sessions.sessionstags()
  ['foo', 'root']

This section is not by default activated:

.. code-block:: python

  >>> fs = sessions.ticket(tag='foo')
  >>> fs
  <vortex.sessions.Ticket object at 0x10278d0>
  >>> fs.tag
  'foo'
  >>> fs.active
  False
  >>> sessions.current().tag
  'root'

Setting an active session
=========================

The active character of a session could be defined at creation time through the appropriate ``active`` boolean argument:

.. code-block:: python

  >>> from vortex import sessions
  >>> rs = sessions.current()
  >>> rs.tag
  'root'
  >>> rs.active
  True
  >>> fs = sessions.ticket(tag='foo', active=True)
  >>> fs.tag
  'foo'
  >>> fs.active
  True
  >>> rs.active
  False

The decision to switch from the current session to an other one could be taken
at any time through the :func:`vortex.sessions.switch` mechanism:

.. code-block:: python

  >>> from vortex import sessions
  >>> rs = sessions.current()
  >>> fs = sessions.ticket(tag='foo')
  >>> sessions.sessionstags()
  ['foo', 'root']
  >>> sessions.switch('foo')
  <vortex.sessions.Ticket object at 0x7f4b7a572b10>
  >>> rs.active
  False
  >>> sessions.current().tag
  'foo'

=============
Vortex gloves
=============

The ability to handle various gloves could be of some importance as soon as the need
to smoothly changes the behavior of global configurations appears.

The default glove
=================

A default glove always preexists to any user action. It is the glove in which the initial vortex import
action has been performed:

.. code-block:: python

  >>> import vortex
  >>> vortex.rootenv.glove
  <vortex.gloves.ResearchGlove object at 0xd6bc90>

It could be more convenient to access to this information through the :mod:`vortex.sessions` module interface:

.. code-block:: python

  >>> from vortex import sessions
  >>> sessions.glove()
  <vortex.gloves.ResearchGlove object at 0xd6bc90>
  >>> sessions.glovestags()
  ['default']

Note the slight semantic difference: in vortex we have a ``root`` session
but a ``default`` global verstatile environment!

Creating a new glove
====================

There is no way to avoid the definition of this default glove which is associated
to the ``root`` session and therefore to current binded environment
(this will be discussed later).

As a :class:`vortex.syntax.footprint.BFootprint` based class, the :class:`vortex.gloves.Glove` derivated classes
could be instanciated through the :func:`vortex.gloves.load` interface method.
This is a bad practice unless you really want to enforce the creation of a new glove, whatever the existings
instances could already exist.

Is is strongly recommanded to go through the :mod:`vortex.sessions` module interface:

.. code-block:: python

  >>> from vortex import sessions
  >>> sessions.glove()
  <vortex.gloves.ResearchGlove object at 0x19cdcd0>
  >>> sessions.glove(tag='foo')
  <vortex.gloves.ResearchGlove object at 0x19df9d0>
  >>> sessions.glovestags()
  ['default', 'foo']

Doing so, one could combined a new glove declaration and the activation of a new session using that glove:

.. code-block:: python

  >>> from vortex import sessions
  >>> ng = sessions.glove(tag='foo', user='speedy')
  >>> ng
  <vortex.gloves.ResearchGlove object at 0x15fe990>
  >>> print ng.idcard()
  User     : speedy
  Profile  : research
  Vapp     : play
  Vconf    : sandbox
  Configrc : /home/realuser/.vortexrc
  >>> ns = sessions.ticket(tag='newsession', active=True, glove=ng)
  >>> ns.active
  True
  >>> ns.glove.tag
  'foo'
  >>> sessions.glovestags()
  ['default', 'foo']
  >>> sessions.glove().tag
  'foo'
  >>> ns.env
  <vortex.tools.env.Environment object at 0x15feb50>
  >>> ns.env.glove
  <vortex.gloves.ResearchGlove object at 0x15fe990>
  >>> ns.env.glove.tag
  'foo'
  >>> sessions.current().tag
  'newsession'

============================
Vortex environment variables
============================

Many features of the class of objects dealing with the environment variables
have been encountered in the previous sections. However, here are some example
of utilisation.

How to get a reference to the current environment ?
===================================================

There is more than one way to put your hands on the environ!
Obviously, asking to the module interface :mod:`vortex.tools.env` is not a bad idea:


.. code-block:: python

  >>> from vortex.tools import env
  >>> e = env.current()
  >>> e
  <vortex.tools.env.Environment object at 0x2333c90>
  >>> e['SHELL']
  '/bin/bash'

But one could also "ask" to the current active session:

.. code-block:: python

  >>> from vortex.tools import env
  >>> from vortex import sessions
  >>> e = env.current()
  >>> e
  <vortex.tools.env.Environment object at 0x2735e10>
  >>> t = sessions.ticket()
  >>> t.env
  <vortex.tools.env.Environment object at 0x2735e10>
  >>> t.env.active()
  True
  >>> e.active()
  True
  >>> e is t.env
  True
  >>>

The stack of activated environment objects could be seen as a class method.
If we continue the previous example, this stack should contains the ``rootenv`` defined
at import time and the environ associated to the current session:

.. code-block:: python

  >>> from vortex import rootenv
  >>> rootenv
  <vortex.tools.env.Environment object at 0x272dc90>
  >>> env.Environment.osstack()
  [<vortex.tools.env.Environment object at 0x272dc90>, <vortex.tools.env.Environment object at 0x2735e10>]


Various ways to access to a variable
====================================

When some variable does not exists, ``None`` is returned:

.. code-block:: python

  >>> e['FOO']
  >>> print e['FOO']
  None

Access to a variable could be done through the standard dictionary syntax or as an attribute.
This is not cas sensitive:

.. code-block:: python

  >>> e.foo = 2
  >>> print e['FOO']
  2
  >>> e.Foo
  2

Complex data could be stored in the Environment object. Its shell representation is then accessible
through the :func:`vortex.tools.env.Environment.native` method:
    
.. code-block:: python

  >>> from vortex import toolbox
  >>> f = toolbox.container(file='foo.txt')
  >>> e.file = f
  >>> e.file
  <vortex.data.containers.File object at 0x234fb10>
  >>> e.native('FILE')
  '{"file": "foo.txt"}'
  >>> import os
  >>> os.environ['FILE']
  '{"file": "foo.txt"}'
