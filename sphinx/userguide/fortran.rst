.. _fortran-usage:

*************************
Fortran usage with VORTEX
*************************


In the course of VORTEX usage, such as dealing with Algo Components (cf. :mod:`vortex.algo.components`),
it is necessary to handle some FORTRAN objects. Therefore some basic functionalities have been integrated.
But most of them could be used as standalone tools, without the other parts of the VORTEX toolbox.

The present documentation explains how to manipulate FORTRAN items, mostly namelists,
through the module :mod:`vortex.tools.fortran`.

================
Parsing literals
================

A default literal parser is provided in the fortran module:

.. code-block:: python

  >>> from vortex.tools import fortran
  >>> lp = fortran.LiteralParser()
  >>> lp
  <vortex.tools.fortran.LiteralParser object at 0x7f14cc204b50>

Checking fortran types
======================

Basic fortran types could be checked agains a string value:
    
.. code-block:: python

  >>> lp.check_integer('2')
  True
  >>> lp.check_integer('2.')
  False
  >>> lp.check_integer('2x')
  False
  >>> lp.check_real('1.2E-6')
  True
  >>> lp.check_logical('.T.')
  False
  >>> lp.check_logical('.True.')
  True
  >>> print lp.false.match('.f.')
  <_sre.SRE_Match object at 0x1d2b7e8>
  >>> print lp.true.match('.f.')
  >>> None

Effective types are: integer, boz, real, complex, character, logical.

Parsing fortran types
=====================

After a successful type check, one can parse a specific fortran type
according to the corresponding method of the LiteralParser:

.. code-block:: python

  >>> s = '1.2E-6'
  >>> lp.check_real(s)
  True
  >>> x = lp.parse_real(s)
  >>> print x
  0.0000012

It could be more convenient to use the generic :func:`vortex.tools.fortran.LiteralParser.parse` method:

.. code-block:: python

  >>> x = lp.parse('.true.')
  >>> print x
  True
  >>> type(x)
  <type 'bool'>
  >>> x = lp.parse('2.')
  >>> print x
  2
  >>> type(x)
  <class 'decimal.Decimal'>


Encoding fortran types
======================

The reverse operation could be achieved through a specific encoding function:

.. code-block:: python

  >>> x = 2
  >>> lp.encode_real(x)
  '2.'
  >>> lp.encode_integer(x)
  '2'
  >>> lp.encode_complex(x)
  '(2.,0.)'
  >>> lp.encode_logical(x)
  '.TRUE.'

It is possible to rely on the internal python type to decide which is the appropriate encoding
through the generic :func:`vortex.tools.fortran.LiteralParser.encode` method:

.. code-block:: python

  >>> x = 2
  >>> lp.encode(x)
  '2'
  >>> z = 1 - 2j
  >>> lp.encode(z)
  '(1.,-2.)'


=================
Parsing namelists
=================

A default namelist parser is provided in the fortran module:

.. code-block:: python

  >>> from vortex.tools import fortran
  >>> np = fortran.NamelistParser()
  >>> np
  <vortex.tools.fortran.NamelistParser object at 0x1d465d0>

The namelist parser
===================

The source of the namelist to parse could be given as a source string, a filename or a file descriptor.
If at least one namelist block could be identified, a string given as an argument is directly parsed:

.. code-block:: python

  >>> namsrc = '&NAMFOO LWORK=.FALSE., NRETRY=0/'
  >>> np.parse(namsrc)
  {'NAMFOO': <NamelistBlock: NAMFOO has 2 item(s)>}

If it is not the case, the string is assumed to be a filename, which is opened and read:

.. code-block:: python

  >>> np.parse('toto')
  {'NAERAD': <NamelistBlock: NAERAD has 5 item(s)>, 'NAIMPO': <NamelistBlock: NAIMPO has 0 item(s)>}

The user could also provide a opened file descriptor:

.. code-block:: python

  >>> nd = open('toto', 'r')
  >>> np.parse(nd)
  {'NAERAD': <NamelistBlock: NAERAD has 5 item(s)>, 'NAIMPO': <NamelistBlock: NAIMPO has 0 item(s)>}
  >>> nd.close()


Playing around with namelist blocks
===================================

The output of the parse function is a pure dictionary where keys are namelist names
and values the associated namelist block as a :class:`vortex.tools.fortran.NamelistBlock` object.

So accessing to a namelist block is easy as any dict manipulation:

.. code-block:: python

  >>> nam = np.parse('namelistfc')
  >>> for k, v in sorted(nam.iteritems()):
  ...   print k, v
  ...
  NACIETEO <NamelistBlock: NACIETEO has 0 item(s)>
  NACOBS <NamelistBlock: NACOBS has 0 item(s)>
  NACTAN <NamelistBlock: NACTAN has 0 item(s)>
  ...

A specific namelist block is accessed through is key-name:

.. code-block:: python

  >>> print nam['NAMPAR0']
  <NamelistBlock: NAMPAR0 has 8 item(s)>

Such a block behaves almost as a dictionary:

.. code-block:: python

  >>> nb = nam['NAMPAR0']
  >>> len(nb)
  8
  >>> nb.keys()
  ['MBX_SIZE', 'MP_TYPE', 'NOUTPUT', 'NPRGPEW', 'NPRGPNS', 'NPROC', 'NPRTRV', 'NPRTRW']
  >>> nb['MP_TYPE']
  [2]

It must be stressed that any namelist value is a list of values, to be coherent with the fortran syntax
of the namelist. Such values could be accessed as key-name of the pseudo-dict block or as fake attributes:

.. code-block:: python

  >>> nb.mp_type
  [2]
  >>> nb.mp_type = [ 4 ]
  >>> nb.lfoo = [ True ]
  >>> print nb.dumps()
   &NAMPAR0
     MBX_SIZE=128000000,
     MP_TYPE=4,
     NOUTPUT=1,
     NPRGPEW=1,
     NPRGPNS=NBPROC,
     NPROC=NBPROC,
     NPRTRV=1,
     NPRTRW=NBPROC,
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


==========================
Handling namelist contents
==========================

We have seen that the output of the parse command of a :class:`vortex.tools.fortran.NamelistParser`
object produces a dictionary of :class:`vortex.tools.fortran.NamelistBlock` values which could be handle as such.
However it is possible to go a bit further with the :class:`common.data.namelists.NamelistContent`.

Namelist content as internal resource content
=============================================

In fact the :class:`common.data.namelists.NamelistContent` is defined as the default content class
resources of the kind ``namelist`` derivated from class :class:`common.data.namelists.Namelist`.
But this class :class:`common.data.namelists.NamelistContent`, could be used as a standalone class,
as much of the :class:`vortex.data.contents.DataContent`:

.. code-block:: python

  >>> from common.data.namelists import NamelistContent
  >>> nc = NamelistContent()
  >>> nc
  <common.data.namelists.NamelistContent object at 0x17e6790>
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

Combining namelist content and resource container
=================================================

Instead of starting from scratch, it is obviously possible to merge from a dictionnary of
already defined :class:`vortex.tools.fortran.NamelistBlock` values, but is also possible
to provide the :class:`common.data.namelists.NamelistContent`
with a :class:`vortex.data.containers.Container` derived object:

.. code-block:: python

  >>> from vortex import toolbox
  >>> fc = toolbox.container(file='namelistfc')
  >>> from common.data.namelists import NamelistContent
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

The ``setmacro`` method propagates the specified value of the macro to any block using it:

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

It is also possible to specify a block to exclude from the next merge operation involving
the current namelist content as a delta:

.. code-block:: python

  >>> nc.toremove('NEMVAR')
  >>> nc.rmblocks()
  set(['NEMVAR'])

The same kind of operation exists at the block level:

.. code-block:: python

  >>> nb = nc['NAMPAR0']
  >>> nb.todelete('MP_TYPE')
  >>> nb.rmkeys()
  set(['MP_TYPE', 'MBX_SIZE'])

Finaly the ``merge`` operates fine grain fusion between a namelist content and
whatever bahaves as a dictionary of :class:`vortex.tools.fortran.NamelistBlock` values
(so does an other :class:`common.data.namelists.NamelistContent`):

  >>> from vortex import toolbox
  >>> fc = toolbox.container(file='namelistfc')
  >>> from common.data.namelists import NamelistContent
  >>> nc = NamelistContent()
  >>> nc.slurp(fc)
  >>> from vortex.tools.fortran import NamelistBlock
  >>> nb = NamelistBlock('NAMPAR0')
  >>> nb.mp_type=1
  >>> nb.todelete('MBX_SIZE')
  >>> nc.merge(dict(thisblock = nb))
