.. _fortran-usage:

********************************************
Fortran namelist usage with Bronx and VORTEX
********************************************

In the course of VORTEX usage, such as dealing with Algo Components (cf. :mod:`vortex.algo.components`),
it is necessary to handle some FORTRAN objects. Therefore some basic functionalities have been integrated.
But most of them could be used as standalone tools, without the other parts of the VORTEX toolbox.

The present documentation explains how to manipulate FORTRAN items, mostly namelists,
through the module :mod:`bronx.datagrip.namelist`.

================================================================
Parsing namelists with the bronx package (independant of VORTEX)
================================================================

A default namelist parser is provided in the fortran module:

.. code-block:: python

  >>> from bronx.datagrip import namelist
  >>> np = namelist.NamelistParser()
  >>> np
  <bronx.datagrip.namelist.NamelistParser object at 0x1d465d0>

The namelist parser
===================

The source of the namelist to parse could be given as a source string, a filename or a file descriptor.
If at least one namelist block could be identified, a string given as an argument is directly parsed:

.. code-block:: python

  >>> namsrc = '&NAMFOO LWORK=.FALSE., NRETRY=0/'
  >>> nset = np.parse(namsrc)
  >>> nset
  <bronx.datagrip.namelist.NamelistSet object at 0x7f258aae7c90>
  >>> nset.as_dict()
  {'NAMFOO': <bronx.datagrip.namelist.NamelistBlock object at 0x7f258c4b7250 | name=NAMFOO len=2>}


If it is not the case, the string is assumed to be a filename, which is opened and read:

.. code-block:: python

  >>> nset = np.parse('toto')

The user could also provide a opened file descriptor:

.. code-block:: python

  >>> nd = open('toto', 'r')
  >>> nset = np.parse(nd)
  >>> nd.close()


Playing around with namelist blocks
===================================

The output of the parse function is a :class:`~bronx.datagrip.namelist.NamelistSet` object that
behaves as a dictionary where keys are namelist names and values the associated namelist block
as a :class:`~bronx.datagrip.namelist.NamelistBlock` object.

So accessing to a namelist block is easy as any dict manipulation:

.. code-block:: python

  >>> nam = np.parse('namelistfc')
  >>> for k, v in sorted(nam.items()):
  ...   print k, repr(v)
  ...
  NACIETEO <bronx.datagrip.namelist.NamelistBlock object at 0x... | name=NACIETEO len=0>
  NACOBS <bronx.datagrip.namelist.NamelistBlock object at 0x... | name=NACOBS len=0>
  NACTAN <bronx.datagrip.namelist.NamelistBlock object at 0x... | name=NACTAN len=0>
  ...

A specific namelist block is accessed through is key-name:

.. code-block:: python

  >>> print nam['NAMPAR0']
   &NAMPAR0
     MBX_SIZE=128000000,
     MP_TYPE=4,
     NOUTPUT=1,
     NPRGPEW=1,
     NPRGPNS=__NBPROC__,
     NPROC=__NBPROC__,
     NPRTRV=1,
     NPRTRW=__NBPROC__,
     LFOO=.TRUE.,
   /

Such a block behaves almost as a dictionary:

.. code-block:: python

  >>> nb = nam['NAMPAR0']
  >>> len(nb)
  8
  >>> list(nb.keys())
  ['MBX_SIZE', 'MP_TYPE', 'NOUTPUT', 'NPRGPEW', 'NPRGPNS', 'NPROC', 'NPRTRV', 'NPRTRW']
  >>> nb['MP_TYPE']
  2

It must be stressed that any namelist value is a list of values, to be coherent with the fortran syntax
of the namelist. Such values could be accessed as key-name of the pseudo-dict block or as fake attributes:

.. code-block:: python

  >>> nb.mp_type
  2
  >>> nb.mp_type = [ 4, 5 ]
  >>> nb.lfoo = [ True ]
  >>> print nb.dumps()
   &NAMPAR0
     MBX_SIZE=128000000,
     MP_TYPE=4,5,
     NOUTPUT=1,
     NPRGPEW=1,
     NPRGPNS=__NBPROC__,
     NPROC=__NBPROC__,
     NPRTRV=1,
     NPRTRW=__NBPROC__,
     LFOO=.TRUE.,
   /

We can see that some values are not valid fortran values. They are identified as macros, to be substituted
(or not) at dump time:

.. code-block:: python

  >>> nb.macros()
  ['NBPROC']
  >>> nb.addmacro('NBPROC', 24)
  >>> print nb.dumps()
   &NAMPAR0
     MBX_SIZE=128000000,
     MP_TYPE=4,
     NOUTPUT=1,
     NPRGPEW=1,
     NPRGPNS=24,
     NPROC=24,
     NPRTRV=1,
     NPRTRW=24,
     LFOO=.TRUE.,
   /


=========================================================
Handling namelist contents (this part is VORTEX specific)
=========================================================

We have seen that the output of the parse command of a :class:`~bronx.datagrip.namelist.NamelistParser`
object produces a dictionary-like object (:class:`~bronx.datagrip.namelist.NamelistSet`) that
contains :class:`~bronx.datagrip.namelist.NamelistBlock` values.

However it is possible to go a bit further with the :class:`vortex.nwp.data.namelists.NamelistContent`.

Namelist content as internal resource content
=============================================

In fact the :class:`vortex.nwp.data.namelists.NamelistContent` is defined as the default content class
resources of the kind ``namelist`` derivated from class :class:`vortex.nwp.data.namelists.Namelist`.
But this class :class:`~vortex.nwp.data.namelists.NamelistContent`, could also be used as a standalone
class, as much of the :class:`vortex.data.contents.DataContent`:

.. code-block:: python

  >>> from vortex.nwp.data.namelists import NamelistContent
  >>> nc = NamelistContent()
  >>> nc
  <vortex.nwp.data.namelists.NamelistContent object at 0x17e6790>
  >>> len(nc)
  0

Named or anonymous creation of block is possible:

.. code-block:: python

  >>> nc.newblock()
  <NamelistBlock: AUTOBLOCK001 has 0 item(s)>
  >>> nc.newblock()
  <NamelistBlock: AUTOBLOCK002 has 0 item(s)>
  >>> nc.newblock('NAMSPACE')
  <NamelistBlock: NAMSPACE has 0 item(s)>
  >>> nb = nc.get('AUTOBLOCK001')
  >>> nb
  <NamelistBlock: AUTOBLOCK001 has 0 item(s)>
  >>> nb.foo = 2
  >>> print nc.dumps()
   &AUTOBLOCK001
     FOO=2,
   /
   &AUTOBLOCK002
   /
   &NAMSPACE
   /

All of the methods of the :class:`~bronx.datagrip.namelist.NamelistSet`
class are available in the :class:`~vortex.nwp.data.namelists.NamelistContent` and
compatibility is ensured.

However, some extra methods are added in order to work with Vortex's resource and
container but also to include a list of predefined macros.

Combining namelist content and resource container
=================================================

Instead of starting from scratch, it is obviously possible to merge from a dictionnary of
already defined :class:`~bronx.datagrip.namelist.NamelistBlock` values, but is also possible
to provide the :class:`~vortex.nwp.data.namelists.NamelistContent` with a
:class:`vortex.data.containers.Container` derived object:

.. code-block:: python

  >>> from vortex import toolbox
  >>> fc = toolbox.container(file='namelistfc')
  >>> from vortex.nwp.data.namelists import NamelistContent
  >>> nc = NamelistContent()
  >>> nc.slurp(fc)
  >>> len(nc)
  159
  >>> print nc['NAMPAR0'].dumps()
   &NAMPAR0
     MBX_SIZE=128000000,
     MP_TYPE=2,
     NOUTPUT=1,
     NPRGPEW=1,
     NPRGPNS=NBPROC,
     NPROC=NBPROC,
     NPRTRV=1,
     NPRTRW=NBPROC,
   /
  >>> nc['NAMPAR0'].mp_type = 1
  >>> nc.rewrite(fc)
  >>> fc.close()


Advanced methods
================

The :meth:`~vortex.nwp.data.namelists.NamelistContent.setmacro` method propagates the specified value
of the macro to any block using it:

.. code-block:: python

  >>> nc.setmacro('NBPROC', 2)
  >>> print nc['NAMPAR0'].dumps()
   &NAMPAR0
     MBX_SIZE=128000000,
     MP_TYPE=2,
     NOUTPUT=1,
     NPRGPEW=1,
     NPRGPNS=2,
     NPROC=2,
     NPRTRV=1,
     NPRTRW=2,
   /

The :meth:`~vortex.nwp.data.namelists.NamelistContent.merge` method is abled to merge a
:class:`~vortex.nwp.data.namelists.NamelistContent` object with another
:class:`~vortex.nwp.data.namelists.NamelistContent` or with a raw
:class:`~bronx.datagrip.namelist.NamelistSet` object.
