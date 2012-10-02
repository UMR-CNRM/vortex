.. _source:

Source layout
=============

The hierarchy of files is as follow:

- examples
- gco
- mercator
- olive
- sandbox
- test
- vortex

vortex
++++++

The source kernel of the VORTEX toolbox!


sandbox
+++++++

Extra modules used mostly for dev purpose.


gco
+++

Plugin package.
Some classes of resources and predefined attributes to deal with the GCO environment.

mercator
++++++++

Plugin package.
Some classes of resources the MERCATOR project would like to insert.

olive
+++++

Plugin package.
Some classes of resources the OLIVE project is particularly found of.


examples
++++++++

The following programs acts as high level tests.
This is a good idea to rerun these examples after a nice set of modifications.

test
++++

Test suites using :class:`TestSuite`, :class:`TestCase`, :class:`TestLoader`
and :class:`TextTestRunner`.

