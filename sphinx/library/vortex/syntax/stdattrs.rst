:mod:`vortex.syntax.stdattrs` --- Some predefined sets of attributes
====================================================================

.. automodule:: vortex.syntax.stdattrs
   :synopsis: Definition of some standard attributes used in footprint mechanism

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.1


Package
-------

.. autodata:: __all__


Pre-defined attributes as abstract decorative footprints
--------------------------------------------------------

A :class:`DecorativeFootprint` include the footprint's definition for a given
attribute or set of attributes (see above) but also takes care of changing the
class behaviour. 

Examples:

   * The :data:`date_deco` :class:`DecorativeFootprint` object
     will add the date attribute to the footprint, alter the result of the
     ``namebuilding_info`` method (allowing the date to be used in the Vortex's
     pathname) and alter the result of the ``generic_pathname`` method  (allowing
     the date to be used in the Olive or OpArchive pathname).
   * The :data:`month_deco` :class:`DecorativeFootprint` object
     will add the month attribute to the footprint, alter the result of the
     ``namebuilding_info`` method (allowing the month's number to be used in the
     Vortex's basename), alter the result of the ``olive_basename`` method and
     add a ``gget_basename`` method (allowing to fetch the appropriate resource
     when Genv/Gget is used).

.. note: If a method is overwritten manually in the decorated class, the
         :class:`DecorativeFootprint` object will leave it untouched.


.. autodata:: cutoff_deco

.. autodata:: date_deco

.. autodata:: dateperiod_deco

.. autodata:: model_deco

.. autodata:: month_deco

.. autodata:: nativefmt_deco

.. autodata:: term_deco

.. autodata:: timeperiod_deco

.. autodata:: number_deco


Pre-defined attributes as abstract footprints
---------------------------------------------

.. autodata:: xpid

.. autodata:: legacy_xpid

.. autodata:: free_xpid

.. autodata:: actualfmt

.. autodata:: cutoff

.. autodata:: date

.. autodata:: dateperiod

.. autodata:: domain

.. autodata:: model

.. autodata:: month

.. autodata:: nativefmt

.. autodata:: term

.. autodata:: timeperiod

.. autodata:: truncation

.. autodata:: namespacefp

.. autodata:: block

.. autodata:: member

.. autodata:: number

.. autodata:: hashalgo

.. autodata:: compressionpipeline


Pre-defined attributes as dictionaries
--------------------------------------

.. autodata:: a_xpid

.. autodata:: a_legacy_xpid

.. autodata:: a_free_xpid

.. autodata:: a_actualfmt

.. autodata:: a_cutoff

.. autodata:: a_date

.. autodata:: a_domain

.. autodata:: a_model

.. autodata:: a_month

.. autodata:: a_nativefmt

.. autodata:: a_suite

.. autodata:: a_term

.. autodata:: a_truncation

.. autodata:: a_namespace

.. autodata:: a_block

.. autodata:: a_member

.. autodata:: a_number

.. autodata:: a_hashalgo

.. autodata:: a_compressionpipeline


Pre-defined sets
----------------

.. autodata:: models

.. autodata:: binaries

.. autodata:: utilities

.. autodata:: knownfmt

.. autodata:: opsuites


Modeule Interface
-----------------

.. autofunction:: show

Datatypes used in the above abstract footprints
-----------------------------------------------

.. autoclass:: FmtInt
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: XPid
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: LegacyXPid
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: FreeXPid
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Namespace
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Longitude
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Latitude
   :show-inheritance:
   :members:
   :member-order: alphabetical


Utility classes useful to set some footprints defaults
-------------------------------------------------------

.. autoclass:: DelayedEnvValue
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: DelayedInit
   :show-inheritance:
   :members:
   :member-order: alphabetical

