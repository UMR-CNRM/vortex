%%%%%%%%
Glossary
%%%%%%%%

Dictionary of notions in the VORTEX framework :
    
==============================  ==============================  ==============================
..                              Terms                           ..                          
==============================  ==============================  ==============================
:term:`Environment`             :term:`Physical Space`          :term:`Ticket`
:term:`Logical Space`           :term:`Session`                 ..
==============================  ==============================  ==============================

Spaces
------

.. glossary::

   Logical space
      This is the space meaningful in the sense of numerical prediction and methods.
      Most of the time, entities are simply described by plain words by the one
      in charge of the scientific experiments, particularly for the most abstract notions.

      Example::

         Try to describe the sequence that would produce the most acurate analysis every morning.

   Physical space
      This is the *real* space where the entities defined in the logical space take place.
      Very often related to information systems.
   
      Example::

         The specific scheduling of tasks to build the analysis.
	 
      Some descriptors from the logical space could have a second life in the physical one.

      Example::
      
          The logical description of a meteorological resource could lead to the physical
	  localisation of a data resource playing that role.
	  

Logical space
-------------

.. glossary::

   Session
      In the :term:`logical space` the session refers to the most abstract level of the general context
      the user operates.
        
      DevGuide: :ref:`env-interface`

      Modules: :mod:`vortex.sessions`

   Ticket
      This is a shortcut to a :term:`session` ticket.

Physical space
--------------

.. glossary::

   Environment
      The environment refers more precisely to the environment variables.
      Vortex provides the user with a very powerfull interface on top
      of the usual :obj:`os.environ` instance.

      DevGuide: :ref:`env-interface`

      Modules: :mod:`vortex.tools.env`
