.. _env-interface:

**********************************   
Understanding environment features
**********************************


What could be understood as a full featured environment is the combination
of three classes of objects :

* a vortex session :class:`vortex.sessions.Ticket`,
* a global verstatile environment :class:`vortex.gloves.Glove`,
* a active environment binded to operating system :class:`vortex.tools.env.Environment`.

A session Ticket is always binded to a root environment (the one the session was started in),
and each Environment is populated with a Glove. Whether this ticket or environment remains
active, and what "active" means, is an other matter and depends of the current usage.
For the time being, let say that at any time during a vortex experiment, one could
be aware of the current session and current active environment in relation to the current
global versatile environment.


===============
Vortex defaults
===============

Let's start with the default behavior, assuming that the user does not want yet
to hack things behind the scene.

The top level import
====================

At the very begining, one should import the :mod:`vortex` module.

In the import phase a :envvar:`rootenv` is defined. It remains directly accessible at any
time and should not be changed. It is the actual os environment at launch time.

.. code-block:: python

  >>> import vortex
  >>> vortex.rootenv
  <vortex.tools.env.Environment object at 0x2948510>

This environment is given a default glove, such as the one that result from
a empty load without any specific description whatsoever.

.. code-block:: python

  >>> vortex.rootenv.glove
  <vortex.gloves.ResearchGlove object at 0x2949410>

Let's have a look to the init module itself :

.. code-block:: python

  import sessions, algo, data
  from tools import env

  rootenv = env.Environment(active=True)
  rootenv.glove = sessions.glove()

  sessions.ticket(topenv=rootenv, glove=rootenv.glove, prompt='Vortex v-'+__version__+':')

  def ticket():
    return sessions.ticket()

  def sh():
    return sessions.system()


We can see that this :envvar:`rootenv` is the top environment for
the default session created :

.. code-block:: python

  >>> vortex.ticket()
  <vortex.sessions.Ticket object at 0x2962150>
  >>> vortex.ticket().topenv
  <vortex.tools.env.Environment object at 0x2948510>

Which is not the same as the current :envvar:`env` active in that session :

.. code-block:: python

  >>> vortex.ticket().env
  <vortex.tools.env.Environment object at 0x2962210>

If we ask to the :mod:`vortex.tools.env` module which environment is the current one,
it is this last one who is active :

.. code-block:: python

  >>> vortex.tools.env.current()
  <vortex.tools.env.Environment object at 0x2962210>
