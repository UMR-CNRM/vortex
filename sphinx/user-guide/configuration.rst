====================
Configuring *vortex*
====================

The default behavior of *vortex* can be modified by altering the *configuration*.
The configuration is a set of *sections*, which themselves are sets of ``key=value`` pairs.

The configuration can be modified using two functions:

- :py:func:`config.set_config <vortex.config.set_config>`: Set a given key within a section to a value.
- :py:func:`config.load_config <vortex.config.load_config>`: Set multiple keys from a TOML file.

The value of a specific key can be queried using
:py:func:`config.from_confi <vortex.config.from_config>`.  It is also
possible to print the entire configuration using
:py:func:`config.print_config <vortex.config.print_config>`.

.. seealso::

   :doc:`../reference/configuration`
