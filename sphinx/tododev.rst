%%%%%%%%%%%%%%%%%%%%%%%%%%%
Todo list (dev suggestions)
%%%%%%%%%%%%%%%%%%%%%%%%%%%

Suggestions for further developpement, sorted by thematic subjects.

================
1. Documentation
================

syntax
======

expand
------

Extensive doc of the expand mechanism.

rangex
------

Extensive doc of the rangex mechanism.


=======
2. Code
=======

Some coding is expected...


Containers
==========

rewind
------

Double check that everything is ok with virtual iodesc.


External tools
==============

ftget / ftput
-------------

Check the places and conditions to use this tools.


Layout
======

context obs
-----------

Do something when one item is flag on delete.


OLIVE interface
===============

sections
--------

Some graphical rendition of the active status of the section.


Reporting
=========

warnings
--------

Automatically collect warnings or some upper logging information ?


Resources Handlers
==================

format
------

Change keyword "format" to "fmt" for coherency.


refresh
-------

Introduce a refresh information on resource handler:
in case the date is in situ, there could be no need to perform some action
(ex.: namelist, get then namdelta).


namespaces
----------

Introduce some std env value for namespaces gco / op ?

parallel listings
-----------------

Make a clear choice between cat NODE.all and patch/apply container.


Sequences
=========

effective inputs
----------------

After the end of the retrieve sequence, make a report and take action
depending of fatal or not conditions.

input / output log
------------------

Extend the same mechanism as algo log.

nice dump
---------

Use data dumper for messages:

    * could not put / get an incomplete rh
    * store
    * multiple candidates (also: many identical messages, eg. terms)

toolbox input / output
----------------------

Keep track of unsuccesful get / put commands when justdoit active.

Stores
======

flush
-----

Add a facility to perform some optional flush for caches.