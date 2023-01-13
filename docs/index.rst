.. bronx documentation master file, created by
   sphinx-quickstart on Wed Nov  2 14:34:54 2022.
.. :noindex:

Welcome to footprints' package documentation!
=============================================

(Version française de cette documentation : :ref:`footprints_doc_fr`)

The Holy Grail of object programming is that one would like most often not to
have to precisely characterise the object that one wants to use to fulfil a
certain role. At the very least we would not want to have to specify the class
we instantiate to get the object. In most cases, it is sufficient for us to
know that this or that object combines certain qualities or is able to carry
out this or that action. We often find in the object-oriented programming
literature that a good object code is a code where only classes and
never objects are manipulated.

It is a bit of this role of dispenser of objects, based on the simple
description of class characteristics, that the :mod:`footprints` package proposes to
assume. It is this, and a little more, since it will allow (at this stage of the
presentation it will be an act of faith) to ensure the maintainability (in time,
or with regards to behaviour modifications of such and such “object classes”
which would not immediately impose itself on the mind of their creator at the
moment of their conception) and especially the extensibility of any software
package that would consider the :mod:`footprints` package as the basis of its
development. Icing on the cake, we will even see that it ensures interoperability
between different sets of software, provided that they comply with purely formal
conventions.

The idea is very simple. It is a slightly elaborate variation of the factory
design pattern. Instead of accurately describing an object in all its
characteristics (including providing its class), we will take the problem in
reverse and try to answer the question: which class would be likely to
instantiate in an object, which would have characteristics compatible with those
of which I already know?

In other words, you walk down a forest road, and you see bits of mixed
footprints, in the mud for example, or sometimes hidden by a puddle, or torn off
tree leaves, etc., and you wonder: “what is the creature or creatures that
may have left such footprints?”. If ever there is at least one answer to this
question, well, I would like to know it and dispose of it freely, for example,
to evaluate its other characteristics (such depth of footprints can give an
indication of weight for example, etc.) or make him do this or that action (we
say: method ).

Any analogy having its limits, let's play a little bit with this package.

===========
First steps
===========

We can consider this basic component/package from different angles: that of the
user of upper layers of the toolbox that will not notice its existence (hopefully),
or that of the developer who would want to fully enjoy the extensibility offered
by the use of “footprints” as an object factory. In addition, between the two,
lies a large variety of uses. It is up to you to sort it out!

The import of the package does not activate anything at the moment::

    >>> import footprints

What will fundamentally allow the :mod:`footprints` package is to group classes
according to a logic of use that will be specific to each designer, or user.
But, not any class, only classes that will derive from a base type named
:class:`footprints.FootprintBase`.

We will say that these classes are “collected”... by “collectors” which are kind of
catalogues. The :mod:`footprints` package can be asked for the list of collected
classes, or the :mod:`footprints.collectors` module can be asked for the list of
catalogues currently “in use”. If we have done nothing but importing the main
package, these lists are empty of course::

    >>> footprints.collected_classes()
    set([])
    >>> footprints.collectors.keys()
    []

In order to save time later on, we will adopt the following convention::

    >>> import footprints as fp

Our recurrent example will consist in handling some fruits. Two class variables
will be sufficient to characterise footprint classes (characteristics that will
of course be inheritable): the name or names of the collectors to which they wish
to contribute, and their footprint. To illustrate this, let's define a base class
of type ``Fruit`` in the ``fruits`` module.

.. code-block:: python

    class Fruit(fp.FootprintBase):
        _collector = ('fruit',)
        _footprint = dict(
            info = 'Forbidden fruit',
            attr = dict(
                colour = dict(),
            )
        )

If we now query the list of collector names, this one is no longer empty::

    >>> fp.collectors.keys()
    ['fruit']
    >>> fp.collected_classes()
    set([<class 'fruits.Fruit'>])

We could pick up this fruit collector, and ask for a green-coloured fruit for
example::

    >>> cf = fp.collectors.get(tag='fruit')
    >>> print cf
    <footprints.collectors.Collector object at 0x7fb488f77950>
    >>> print cf.tag
    fruit
    >>> p = cf.load(colour='green')
    print p
    <fruits.Fruit object at 0x7fb488f77d10 | footprint=1>

With the :meth:`~footprints.collectors.Collector.load` method of the collector
we have recovered a fruit whose footprint is constituted by an attribute, its
colour, which seems to stick to the skin::

    >>> print p.colour
    green
    >>> p.couleur = 'red'
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/home/sevault/git-dev/vortex/site/footprints/access.py", line 93, in __set__
        raise AttributeError('Read-only attribute [' + self._attr + '] (write)')
    AttributeError: Read-only attribute [colour] (write)
    >>> del p.colour
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/home/sevault/git-dev/vortex/site/footprints/access.py", line 96, in __delete__
        raise AttributeError('Read-only attribute [' + self._attr + '] (delete)')
    AttributeError: Read-only attribute [colour] (delete)

It is already quite nice (being very benevolent). But frankly, it is not as
great as it seems. We could first say that it is a shame to be able to
instantiate a class like ``Fruit``. Obviously, it is an abstract class, so let us
say it right away. Let's start from scratch, define ``Fruit`` as abstract, and
create two very real classes, apples and strawberries::

    class Fruit(fp.FootprintBase):
        _collector = ('fruit',)
        _abstract  = True
        _footprint = dict(
            info = 'Forbidden fruit',
            attr = dict(
                colour = dict(),
            )
        )

    class Apple(Fruit):
        _footprint = dict(
            attr = dict(
                colour = dict(
                    values = ['green', 'yellow', 'red']
                )
            )
        )

    class Strawberry(Fruit):
        _footprint = dict(
            attr = dict(
                colour = dict(
                    values = ['red']
                )
            )
        )

Rather than continuing to request a collector explicitly as we did previously,
which is somewhat laborious, we will use another shortcut from the :mod:`footprints`
package, given by a proxy that allows you to dynamically access all the
collectors that have been created at one time or another at the mercy of module
loadings (we will come back to this important aspect)::

    >>> print fp.proxy
    <footprints.proxies.FootprintProxy object at 0x7f142c28b590>
    >>> fp.proxy.fruits
    <footprints.collectors.Collector object at 0x7f142c28bad0>

Collectors are callable objects, which return the list of classes that can be
instantiated in this category::

    >>> fp.proxy.fruits()
    [<class 'fruits.Apple'>, <class 'fruits.Strawberry'>]

Miracle! As expected, there are only two kinds of fruits collected: ``Apple`` and
``Strawberry``. Now let's ask for some green fruit::

    >>> x = fp.proxy.fruit(colour='green')
    >>> print x
    <fruits.Apple object at 0x7f142c00d390 | footprint=1>

Yes! It's an apple! If I ask for a yellow fruit? Result::

    >>> y = fp.proxy.fruit(colour='yellow')
    >>> print y
    <fruits.Apple object at 0x7f142c00d450 | footprint=1>

And for a blue-coloured fruit::

    >>> b = fp.proxy.fruit(colour='blue')
    # [2015/16/06-16:12:21][footprints.collectors][pickup:0151][WARNING]: No 'fruit' found in description
        dict(
            colour = 'blue',
            fruit = None,
        )

    Report Footprint-Fruit:

        fruits.Strawberry
            couleur    : {'args': 'blue', 'why': 'Not in values'}

        fruits.Apple
            couleur    : {'args': 'blue', 'why': 'Not in values'}

We get an instantiation report that clearly tells us why none of the applicant
classes can be selected, and for good reason obviously (unless you love blue
strawberries).

At this very rudimentary stage of the exposure of the instantiation mechanism by
“footprints”, we can already make some remarks:

  * At no time it is necessary to make assumptions about the number of eligible
    classes;
  * The *a priori* knowledge of the attributes which correspond (or not) to this
    or that class is optional, the mechanism of resolution of the acceptable
    values, will sort it out;
  * It's enough for a class to set a value to its class variable
    :envvar:`_collector` for such a collector to exist;
  * Classes can be defined anywhere in the tree of your package, or in an outer
    package that you would import so that classes inheriting from
    :mod:`footprints.FootprintBase` are automatically collected.

These last two aspects are at the base of the extensibility of any code based on
footprints, and therefore ... on VORTEX.

===================
In case of conflict
===================

This is all very good, but what happens if you ask for a red fruit? Well, here it is::

    >>> r = fp.proxy.fruit(colour='red')
    # [2015/16/06-16:35:48][footprints.collectors][find_best:0203][WARNING]: Multiple fruit candidates
        dict(
            colour = 'red',
        )
    # [2015/16/06-16:35:48][footprints.collectors][find_best:0207][WARNING]: no.1 in.1 is <class 'fruits.Apple'>
    # [2015/16/06-16:35:48][footprints.collectors][find_best:0207][WARNING]: no.2 in.1 is <class 'fruits.Strawberry'>

You get a great warning because there are multiple choices. This is not necessarily
a problem. In everyday life, if you ask for a chair, it is probably for sitting,
no matter whether it is made of plastic or wood. Here in our test example, the
confusion between the outer colour of the fruit and its flesh is more delicate.
However, we will do with it. The question is what to do if you have to be able
to distinguish the colour. On the other hand, more exactly and more generally:
according to which criteria will compatible footprints be distinguished?

In this case, the "footprints" package uses a rather intuitive heuristic: the
sorting takes place according to the priority level and the number of attributes
recognised in the footprint.

In the case of apples and strawberries, as the classes have been defined, there
is no distinction in terms of priority and they both have a single attribute. It
would be nice to elaborate a little bit on that.

Priority levels
---------------

The :mod:`footprints` package defines by default a priority level for each
object with a footprint.

Let's look at the “apple” for example::

    >>> print x.footprint_level()
    DEFAULT

If we take a closer look, the :mod:`footprints.priorities` module has defined a
set of priorities named :envvar:`top` with some default levels::

    >>> print fp.priorities.top
    <footprints.priorities.PrioritySet object at 0x7f142c275f90>
    >>> print fp.priorities.top.levels
    ('NONE', 'DEFAULT', 'TOOLBOX', 'DEBUG')

They are accessible directly, and ordered from each other::

    >>> top = fp.priorities.top
    >>> print top.DEFAULT
    <footprints.priorities.PriorityLevel object at 0x7f142c2810d0>
    >>> print top.TOOLBOX
    <footprints.priorities.PriorityLevel object at 0x7f142c281110>
    >>> top.DEFAULT > top.TOOLBOX
    False

All imaginable operations on such a priority set are obviously provided:
insertions, permutations, eliminations, etc. In the vortex context, for example,
we start with this simple sequence of modification of the order of priorities,
just after the :mod:`footprints` package is imported::

    >>> fp.priorities.set_before('debug', 'olive', 'oper')
    >>> top.levels
    ('NONE', 'DEFAULT', 'TOOLBOX', 'OLIVE', 'OPER', 'DEBUG')

One could imagine that strawberries have a higher priority than apples, because
apples they are kept longer. The declaration of the footprint of the class would
then be::

    class Strawberry(Fruit):
        _footprint = dict(
            attr = dict(
                colour = dict(
                    values = ['red']
                )
            ),
            priority = dict(
                level = fp.priorities.top.TOOLBOX
            ),
        )

Let's go back to our previous selection::

    >>> r = fp.proxy.fruit(colour='red')
    # [2015/16/06-17:05:01][footprints.collectors][find_best:0203][WARNING]: Multiple fruit candidates
      dict(
          colour = 'red',
      )
    # [2015/16/06-17:05:01][footprints.collectors][find_best:0207][WARNING]: no.1 in.1 is <class 'fruits.Strawberry'>
    # [2015/16/06-17:05:01][footprints.collectors][find_best:0207][WARNING]: no.2 in.1 is <class 'fruits.Apple'>

There is always a warning message because, in fact, there still are several fruit
candidates, but strawberry will inevitably win the competition!

But we also said that the number of attributes corresponding to a given
footprint would be taken into account. This is only possible if one can or can
not provide an attribute. In other words, if a class has optional attributes in
its footprint.

Optional attributes
-------------------

We will now give the apple an optional attribute, namely the name of the
producer. It is well known that strawberries are produced in Spain, above
ground, by public limited companies, and therefore will not have such an
attribute. The complete declaration now looks like this::

    class Apple(Fruit):
        _footprint = dict(
            attr = dict(
                colour = dict(
                    values = ['green', 'yellow', 'red']
                ),
                producer = dict(
                    optional = True,
                    default = 'Jacques',
                )
            )
        )

What happens when you choose a red fruit? This happens::

    >>> r = fp.proxy.fruit(colour='rouge', producer='marcel')
    # [2015/16/06-17:14:34][footprints.collectors][find_best:0203][WARNING]: Multiple fruit candidates
        dict(
            colour = 'rouge',
            producer = 'marcel',
        )
    # [2015/16/06-17:14:34][footprints.collectors][find_best:0207][WARNING]: no.1 in.1 is <class 'fruits.Strawberry'>
    # [2015/16/06-17:14:34][footprints.collectors][find_best:0207][WARNING]: no.2 in.2 is <class 'fruits.Apple'>

Since the resolution is first prioritized, a strawberry is always selected
first.

If we return to two categories of fruits of identical priority (hypothesis for
the rest of the tutorial, unless otherwise stated), we would then have::

    >>> r = fp.proxy.fruit(colour='rouge', producer='Marcel')
    # [2015/16/06-17:21:10][footprints.collectors][find_best:0203][WARNING]: Multiple fruit candidates
        dict(
            colour = 'rouge',
            producer = 'Marcel',
        )
    # [2015/16/06-17:21:10][footprints.collectors][find_best:0207][WARNING]: no.1 in.2 is <class 'fruits.Apple'>
    # [2015/16/06-17:21:10][footprints.collectors][find_best:0207][WARNING]: no.2 in.1 is <class 'fruits.Strawberry'>

Here, the apple is inevitably selected because it has two attributes that
correspond to the footprint. Of course, we now have the “producer” attribute for
the apple in question::

    >>> print r.producteur
    Marcel

As it is optional, the “producer” does not necessarily find himself in the
footprint. The default value is in this case assigned to the attribute::

    >>> p = fp.proxy.fruit(colour='verte')
    >>> print p.producteur
    Jacques

===========
Inheritance
===========

Now, glancing over our shoulder, we can see that the classes we want to make
eligible for the footprint instantiation mechanism must inherit from a base
class named :class:`footprints.FootprintBase` and define their footprint via the
**_footprint** class variable.

In fact, even though we have defined this **_footprint** as a basic Python
structure (dict), it is automatically transformed into an object of class
:class:`footprints.Footprint` when the class is created by the Python interpreter
(actually by the meta-class used to instantiate this class, but it would take us
a little too deep into the package internals).

By cheating somewhat with the rules of access to the “hidden” attributes of the
class (i.e.: preceded by an underscore), this is something we can easily check::

    >>> fruits.Apple
    <class 'fruits.Apple'>
    >>> fruits.Apple._footprint
    <footprints.Footprint object at 0x7f9ef0bf19d0>

The clean way to retrieve the footprint object associated with a class is to use
the :meth:`~footprints.FootprintBase.footprint_retrieve` class method::

    >>> fruits.Apple.footprint_retrieve()
    <footprints.Footprint object at 0x7f9ef0bf19d0>

For the most curious, we will see later the methods that apply to this object.
But what interests us is to know how this composition relationship (the class and
its object footprint) behaves in case of inheritance.

Class inheritance
-----------------

In terms of classical Python's inheritance, there is nothing new brought by the
classes derived from :class:`footprints.FootprintBase`: in the absence of any new
redefinition of their footprint, they “recover” an identical footprint to that
of the parent class.

**Warning**: identical means that it has all the qualities and properties but
without being the same object! As we can see in this short example::

    >>> class GrannySmith(fruits.Apple):
            pass
    >>> GrannySmith.footprint_retrieve()
    <footprints.Footprint object at 0x7f9eedde04d0>

By construction, such a class has therefore the same footprint as its parent
class, and it will therefore be on any occasion “competing” with its parent
class in the instantiation mechanisms that follows. Why not. For example, one can
only focus on redefining or extending one's class methods. But it is much more
likely that one wishes rather to modify one's footprint following the inheritance
concept.

Footprint overloading
---------------------

This is where the object factory makes sense. In the definition of a child
class it will be possible to overload the footprint of the parent class, only
for what needs to be, which does not exclude, of course, to be redundant and to
redefine as identical a characteristic of the footprint (to shield the thing or
simply because we have no certainty on the detail of the footprint of the class
that we inherit from).

Take our beautiful Granny Smith apple, which we write in a module named
:file:`orchad.py` for example::

    class GrannySmith(fruits.Apple):
        _footprint = dict(
            attr = dict(
                colour = dict( values = ['green'] ),
                size = dict( values = range(3, 8) ),
            ),
        )

We can now imagine that any big green fruit will be a Granny Smith. Let's
check::

    >>> import orchad
    >>> fp.proxy.fruits()
    [<class 'orchad.GrannySmith'>, <class 'fruits.Strawberry'>, <class 'fruits.Apple'>]
    >>> fp.proxy.fruit(colour='green', size=7)
    <orchad.GrannySmith object at 0x7fd427e5a610>

And if you are a little lost, it is always possible to ask the collector of
fruits to draw you the map of the possible attributes::

    >>> fp.proxy.fruits.show_attrmap()
     * size [optional]:
         GrannySmith            + orchad
                                 | values = 3, 4, 5, 6, 7

     * colour:
         Strawberry             + fruits
                                 | values = red
         GrannySmith            + orchad
                                 | values = green
         Apple                  + fruits
                                 | values = yellow, green, red

     * producer [optional]:
         GrannySmith            + orchad
         Apple                  + fruits

Therefore, there is a kind of “merge” of footprints in the order of inheritance
of the classes. Which is both very intuitive and very powerful. Finally,
footprints can be defined directly by an object or a list of objects. For
example, let's build a car as an assembly of an engine and a bodywork::

    traction = fp.Footprint(
        attr = dict(
            horsepower = dict(
                values = [70, 90, 110, 125],
            ),
            animal = dict(
                type = bool,
                optional = True,
                default = False,
            ),
        )
    )

    passenger_compartment = fp.Footprint(
        attr = dict(
            comfort = dict(
                values = ['cosy', 'correct', 'rudimentary'],
                optional = True,
                default = 'correct',
            ),
        )
    )

    class Car(fp.FootprintBase):
        _abstract = True
        _collector = ('car', )
        _footprint = [traction, passenger_compartment]

    class Cart(Car):
        _footprint = dict(
            attr = dict(
                animal = dict(
                    values = [True],
                ),
                comfort = dict(
                    default = 'rudimentary',
                )
            )
        )

Which would give for example::

    >>> fp.proxy.cars()
    [<class 'cars.Cart'>]
    >>> c = fp.proxy.car(horsepower=70, animal=True)
    >>> c
    <cars.Cart object at 0x7f9a257b1150>
    >>> c.animal
    True
    >>> c.comfort
    'rudimentary'

=====================================
General characteristics of footprints
=====================================

We will now review the different features that make possible to refine the
footprint definitions.

Typing
------

An attribute is considered a string of characters by default, but it can be any
other class, whether it is a basic type of Python or a user-defined class.

Imagine that we now want, for each fruit, to give it a size, represented by an
integer between 1 and 6, with a default value of 2. It is enough to modify the
base class definition as follows::

    class Fruit(fp.FootprintBase):
        _collector = ('fruit',)
        _abstract  = True
        _footprint = dict(
            info = 'Forbidden Fruit',
            attr = dict(
                colour = dict(),
                size = dict(
                    type = int,
                    optional = True,
                    default = 2,
                    values = range(1, 7),
                )
            ),
        )

Let's take again what we know to be an apple::

    >>> p = fp.proxy.fruit(colour='green')
    >>> print p.size
    2

Now let's try another numeric value expressed as a base string::

    >>> p = fp.proxy.fruit(colour='green', size='04')
    >>> print p.size
    4

The conversion of type (or *cast*), as long as it is valid (in the sense of what
the constructor of the class specified as the attribute type can accept), is
done automatically. Otherwise, it fails::

    >>> x = fp.proxy.fruit(colour='green', size='rectangle')
    # [2015/16/06-19:36:39][footprints.collectors][pickup:0151][WARNING]: No 'fruit' found in description
        dict(
            size = 'rectangle',
            colour = 'green',
            fruit = None,
        )

    Report Footprint-Fruit:

        fruits.Strawberry
            colour     : {'args': 'green', 'why': 'Not in values'}
            size       : {'args': ('int', 'rectangle'), 'why': 'Could not reclass'}
            size       : {'args': None, 'why': 'Not in values'}

        fruits.Apple
            size       : {'args': ('int', 'rectangle'), 'why': 'Could not reclass'}
            size       : {'args': None, 'why': 'Not in values'}

Allowed values
--------------

We have had multiple opportunities to specify acceptable values for a footprint
attribute with the **values** element. This is particularly convenient for
distinguishing object families, since any proposed value that does not match the
range of allowed values will not allow this class to be instantiated. It can
also be used to code specific methods for this or that class, without crawling
the code with plenty of “if”.

However, this may also make it possible to temporarily characterise a treatment
(for purposes of adjustment or debugging, for example).

The only additional thing to know is that the specified values are automatically
retyped to the type specified for the current attribute. In the case of size for
example, we could have given mandatory values.

Prohibited values
-----------------

As convenient, it is possible to specify the totally prohibited values. In other
words, an object of this class could not have left a footprint of such and such
value. The class is no longer eligible for the instantiation process. This
**outcast** key allows specifying prohibited values. Like the values associated
with the **values** key, they are automatically retyped to the type specified
for the current attribute.

Here is an example with a fruit that cannot reasonably grow in certain
latitudes::

    class Pineapple(Fruit):
        _footprint = dict(
            attr = dict(
                origin = dict(
                    outcast = ['Scotland', 'Ireland'],
                )
            )
        )

Let's check::

    >>> a = fp.proxy.fruit(color='orange', origin='Scotland')
    # [2015/17/06-15:25:17][footprints.collectors][pickup:0151][WARNING]: No 'fruit' found in description
        dict(
            colour = 'orange',
            fruit = None,
            origin = 'Scotland',
        )

    Report Footprint-Fruit:

        fruits.Pineapple
            origin     : {'args': 'Scotland', 'why': 'Outcast value'}

        fruits.Strawberry
            colour     : {'args': 'orange', 'why': 'Not in values'}

        fruits.Apple
            colour     : {'args': 'orange', 'why': 'Not in values'}

Change of values on the fly
---------------------------

It may be useful to "translate" a value, whether we want to allow some
approximation, or that we want to restrict the values actually manipulated by
the different instantiated objects later, while leaving a certain latitude of
choice to the user. However, you must declare these “alternative” values in the
allowed values (if there are any that are explicitly defined).

Take for example the case of Granny Smith::

    class GrannySmith(fruits.Apple):
        _footprint = dict(
            attr = dict(
                size = dict(values = range(3, 8)),
                colour = dict(
                    values = ['green', 'lightgreen'],
                    remap  = dict(lightgreen='green'),
                ),
            ),
        )

We are getting::

    >>> p = fp.proxy.fruit(colour='lightgreen', size=5)
    >>> p.fullname()
    'orchad.GrannySmith'
    >>> p.colour
    'green'

Then we can check that a “simple” apple do not do the trick::

    >>> fp.proxy.fruits.report_whynot('fruits.Apple')
    {'fruits.Apple': {'colour': {'args': 'lightgreen', 'why': 'Not in values'}}}

No need to elaborate more on the incredible flexibility that this feature
allows.

Aliases of attribute names
--------------------------

Another way to customise a footprint is to allow different ways of naming
an identical attribute. In the case of fruits, we could have imagined that the
aspect is a synonym for the colour for example, and put it in the generic base
class. In this case, it would only be a convenient way to name a quality of
all the fruits. This is very handy, in terms of evolution of a software package
whose name associations can be used as time goes by.

However, it also proves to be an elegant way to discriminate between identical
footprints. Imagine that this name alias is only used for strawberries. Only
this class of fruit would then be eligible if we use the *aspect* attribute.

.. code-block:: python

    class Strawberry(Fruit):
        _footprint = dict(
            attr = dict(
                colour = dict(
                    values = ['red', 'green'],
                    alias = ('aspect', 'colouring'),
                )
            ),
        )

We need to verify that this does not create a new attribute::

    >>> f = fp.proxy.fruit(aspect='red')
    >>> f.fullname()
    'fruits.Strawberry'
    >>> f.aspect
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    AttributeError: 'Strawberry' object has no attribute 'aspect'
    >>> f.colour
    'red'

Attribute descriptors
---------------------

We have seen above that it is not possible to reposition the value of an attribute
that is part of the footprint created during the instantiation process. The
following reasoning motivates this: if this or that class has been “chosen”
during this selection process, it owes it to the specific values used at that
time. It is therefore not reasonable to change them. New values might have led
to the instantiation of another class.

Nevertheless, one must not be too dogmatic. Some attribute values are so wide,
or simply unrestricted by the *values* key, allowing modifications.

In fact, for each attribute of the footprint, a descriptor (or accessor) is
defined in the Python code (it is not mandatory to understand this, especially
if you have no notion of Python descriptors). The footprints package having
decided to make your life easy, the thing will come down to giving an intuitive
value to a key named *access*. The possible values are:

    * 'rxx' (this is the default: read-only)
    * 'rwx' (read - write)
    * 'rwd' (read - write - delete)

And their counterparts using “weak” references (in which case the stored values
in the attributes are *weakref*):

    * 'rxx-weak' (this is the default: read-only)
    * 'rwx-weak' (read - write)
    * 'rwd-weak' (read - write - delete)

We can then imagine that pineapples exported to Ireland can change of origin
during their passage in Customs, to conform to the local requirements::

    class Pineapple(Fruit):
        _footprint = dict(
            attr = dict(
                origin = dict(
                    outcast = ['Scotland', 'Ireland'],
                    access = 'rwx',
                )
            )
        )

Then here is the fraud::

    >>> a = fp.proxy.fruit(colour='orange', origin='China')
    >>> a.origin
    'China'
    >>> a.origin = 'Costa Rica'
    >>> print a.origin
    Costa Rica

However, we still conform to the footprint of the class::

    >>> a.origin = 'Scotland'
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/home/sevault/git-dev/vortex/site/footprints/access.py", line 54, in __set__
        raise ValueError('Value {0:s} excluded from range {1:s}'.format(str(value), str(list(fpdef['outcast']))))
    ValueError: Value Scotland excluded from range ['Ireland', 'Scotland']

This would also be true for the allowed values, the type of the attribute, etc.

Arguments for attribute type
----------------------------

For the sake of completeness, let’s mention the last possible key in the
description of a fingerprint attribute, namely the arguments that will be passed
during the automatic typing of the value. We enter here into subtleties whose
utility is difficult to perceive from the outset, but let us simply say that if
we automatically “type” any attribute, it means that we call the constructor for
a given type (*i.e.* a given class), and that it would be a pity to refrain from
being able to pass certain attributes at the last moment. We have very few
cases in the VORTEX... that we will comment... or not!

This option should be in the form of a dictionary, as in this example of an
imaginary bottles module::

    class Volume(int):
        def __new__(cls, value, unit='ml'):
            obj = int.__new__(cls, value)
            obj._unit = unit
            return obj
        def __str__(self):
            return '{0:d}{1:s}'.format(self, self._unit)

    class Container(fp.FootprintBase):
        _abstract = True
        _collector = ('container',)
        _footprint = dict(
            attr = dict(
                volume = dict(
                    type = Volume,
                )
            )
        )

    class Carafe(Contenant):
        _footprint = dict(
            attr = dict(
                volume = dict(
                    args = dict(unit = 'cl'),
                )
            )
        )

In use::

    >>> c = fp.proxy.container(volume=50)
    >>> c.fullname()
    'bottles.Carafe'
    >>> c.volume
    50
    >>> print c.volume
    50cl

Class or object
---------------

Then what happens when the expected type of an attribute is not an object, but a
class? Of course, in Python, the classes themselves are objects. However, we
must be able to distinguish between a type provided for the purpose of
instantiating an attribute value and the fact that we want the attribute itself
to remain a class. This is quite common to think in terms of class collaboration,
or composition. Morality, an optional key is evaluated when resolving footprints,
the key *isclass*.

If set to *True*, then we do not try to instantiate the value of the
attribute in the class given by the *type* key, but we simply check that the
attribute is a subclass of this type.

.. note:: Please add examples ?

==========================
Refine the class selection
==========================

In addition to the *attr*, *info* and *priority* elements we have discussed
above, there is another element of the footprint description that plays an
important role in the footprints resolution mechanism. This is the *only*
component of the footprint.

Using *only* for exact values
-----------------------------

Of course, it can be left blank (and it was the case in all our previous
examples). But when it is filled out, candidate classes for instantiation could
be filtered based on parameters already defined in the footprint or parameters
that could be described as “external” to the footprint itself (and declared in
the default settings).

This selection process only makes sense when the resolution is already a success,
just to check if other stricter (or more dynamic) criteria are met.

We will take a simple example: blue apples appeared in the apple orchards during
the 2001 and 2007 harvests. Only during these years::

    class Zorg(fruits.Apple):
        _footprint = dict(
            attr = dict(
                colour = dict(
                    values = ['blue'],
                ),
            ),
            only = dict(
                harvest = (2001, 2007),
            )
        )

If we do not change our previous attempts, there is little chance of recovering
a blue apple::

    >>> fp.proxy.fruit(colour='bleue')
    # [2015/17/06-20:02:00][footprints.collectors][pickup:0151][WARNING]: No 'fruit' found in description
        dict(
            colour = 'bleue',
            fruit = None,
        )

    Report Footprint-Fruit:

        fruits.Pineapple
            origin     : {'why': 'Missing value'}

        fruits.Strawberry
            colour     : {'args': 'blue', 'why': 'Not in values'}

        fruits.Apple
            colour     : {'args': 'blue', 'why': 'Not in values'}

        orchad.GrannySmith
            colour     : {'args': 'blue', 'why': 'Not in values'}
            size       : {'args': 2, 'why': 'Not in values'}

        orchad.Zorg
            harvest    : {'only': 'No value found', 'args': 'harvest'}

Let's now define, for the whole footprints package, a default harvest date (the
mechanism will be explained later), but which does not correspond to our filter
*only*::

    >>> fp.setup.defaults(harvest=2014)
    >>> fp.proxy.fruit(colour='blue')
    # [2015/17/06-20:10:16][footprints.collectors][pickup:0151][WARNING]: No 'fruit' found in description
        dict(
            colour = 'blue',
            fruit = None,
        )

    Report Footprint-Fruit:

        fruits.Pineapple
            origin     : {'why': 'Missing value'}

        fruits.Strawberry
            colour     : {'args': 'blue', 'why': 'Not in values'}

        fruits.Apple
            colour     : {'args': 'blue', 'why': 'Not in values'}

        orchad.GrannySmith
            colour     : {'args': 'blue', 'why': 'Not in values'}
            size       : {'args': 2, 'why': 'Not in values'}

        orchad.Zorg
            harvest    : {'only': 'Do not match', 'args': (2001, 2007)}

If now we say that the default harvesting year is 2007::

    >>> fp.setup.defaults(harvest=2007)
    >>> fp.proxy.fruit(colour='blue')
    <orchad.Zorg object at 0x7f4281653e90>

Interval based selection
------------------------

For a parameter (or attribute), it is possible to extend the only filter with
the *before_* and *after_* modifiers.

We can thus have a futuristic vision of Zorg apples::

    class Zorg(fruits.Apple):
        _footprint = dict(
            attr = dict(
                colour = dict(
                    values = ['blue'],
                ),
            ),
            only = dict(
                after_harvest = 2033,
            )
        )

In use::

    >>> fp.setup.defaults(harvest=2051)
    >>> fp.proxy.fruit(colour='blue')
    <orchad.Zorg object at 0x7f5f3bee1d10>

We could simultaneously use *before_* and *after_* modifiers, leaving the
designer the choice to specify a non-empty intersection if he/she wants his
class to be instantiated one day.

======================
Substitution mechanism
======================

The values used for footprint class resolution do not need to be all explicit.
It is possible to refer to the values taken by an other footprint's attribute.

.. note:: Please add examples and more details ?

===========
And more...
===========

Multi-collection
----------------

You may not have noticed that the **_collector** class variable took the form
of a :func:`tuple`. So far we have only entered this variable with a single
value. But we could “register” a class with multiple collectors simultaneously,
multiplying the ways in which this class could participate in footprint
resolutions.

To pick up only the beginning of the basic fruit class, we could have written::

    class Fruit(fp.FootprintBase):
        _collector = ('fruit', 'food')
        ...

Our appetising apples or strawberries could then just as easily be obtained by a
request for food::

    >>> fp.collectors.keys()
    ['fruit', 'food']
    >>> fp.proxy.food(colour='yellow')
    <fruits.Apple object at 0x7fd03dd1f0d0>

Reusing instances
-----------------

Instantiating objects is not necessarily expensive. However, there are some
cases where one would prefer to reuse objects that have already come into the
world, since their characteristics would be compatible with what is specified
otherwise in the basic loading mechanism.

This functionality exists: instead of using the
:meth:`~footprints.collectors.Collector.load` method of the collector, we will
use the :meth:`~footprints.collectors.Collector.default` method which has
exactly the same interface. If a compatible object (in the sense of footprints
resolution) has already been created and still exists, it is then returned to us,
otherwise a new one will be created and returned.

This is what we will do with our apples, because apples are good if shared. So it
is better to fetch the same one. To vary pleasure even more, we will use
another way to perform the recovery of our favourite fruit::

    >>> p_adam = fp.load(tag='fruit', colour='yellow')
    >>> p_eve = fp.default(tag='fruit', colour='yellow')
    >>> p_adam is p_eve
    True

Compatibility is a permissive notion, because any value that is not explicitly
rejected can do the trick. We could as well have asked for the second apple::

    >>> p_eve = fp.default(tag='fruit')
    >>> p_adam is p_eve
    True

If we look at the catalogue of all alive instances of fruit (because the
collector also keeps track of the objects he has instantiated), there is only
one fruit, the apple::

    >>> fp.proxy.fruits.instances()
    [<fruits.Apple object at 0x7f350a22a490>]
    >>> p = fp.proxy.fruits.instances().pop()
    >>> p is p_eve
    True
    >>> p.footprint.info
    'Forbidden Fruit'

We will see that some classes of VORTEX correspond quite well to this pattern of
use (the system interface, the execution target, etc.).

Direct instantiation
--------------------

We have seen that the simplest way to get an object that is best suited to what
we know about its characteristics (at least the one that is accessible via the
footprint) is to invoke the :meth:`~footprints.collectors.Collector.load`
method, or even more elegantly, to go through the proxy package.

As it is forbidden to forbid, it turns out to be totally possible to directly
instantiate a class, the hard way, one could say. Let’s get back to our apples::

    >>> p = fruits.Apple(colour='rouge')
    >>> print p.colour
    rouge
    >>> print p.size
    2

In any case, we benefit from all of the footprints resolution mechanisms
previously described: typing, *remapping* value, verification of
allowed or excluded values, etc.

Explicit or implicit
--------------------

The extreme case of the resolution of a footprint would be the case where
there is nothing to solve; for example because all attributes would be optional
and no value would be specified at the time of the resolution.

By default, a class that inherits from :class:`footprints.FootprintBase` must
have at least *one* mandatory attribute. If this is not the case, an exception
is thrown as soon as the Python interpreter creates the class. It is a safeguard
to ensure that a very generic class will not negatively interfere with
footprints resolutions.

Again, there is no absolute rule in this area. It is possible in the declaration
of a class to specify that it does not need to be explicit.

Imagine, a *whatsit* class that is a *thing* with a single optional argument::

    class Whatsit(fp.FootprintBase):
        _collector = ('thing',)
        _footprint = dict(
            attr = dict(
                dummy = dict(
                    optional = True,
                    default = 'euh...',
                )
            )
        )

When loading the Python code, we get:

.. code-block:: python

    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/home/sevault/git-dev/vortex/site/footprints/__init__.py", line 637, in __new__
        raise FootprintInvalidDefinition('Explicit class without any mandatory footprint attribute.')
    footprints.FootprintInvalidDefinition: Explicit class without any mandatory footprint attribute.

So let's go back to our definition, meaning that the class has implicit
resolution::

    class Whatsit(fp.FootprintBase):
        _explicit = False
        _collector = ('thing',)
        _footprint = dict(
            attr = dict(
                dummy = dict(
                    optional = True,
                    default = 'uh...',
                )
            )
        )

There is no loading error anymore and we can now instantiate a thing blindly::

    >>> z = fp.proxy.thing()
    >>> print z
    <__main__.Whatsit object at 0x7f0c61bb1a10 | footprint=1>
    >>> print z.dummy
    uh...

No doubt, science is moving forward...

Online support
--------------

The classes with footprint resolution are self-documenting for all the parts
that are relevant to the footprint's resolution. For the rest, no mystery, you
have to write the generalist doc...

.. code-block:: python

    >>> help(orchad.GrannySmith)

    Help on class GrannySmith in module orchad:

    class GrannySmith(fruits.Apple)
     |  Not documented yet.
     |
     |  Footprint::
     |
     |    dict(
     |        attr = dict(
     |            size = dict(
     |                access = 'rxx',
     |                alias = set([]),
     |                default = 2,
     |                optional = True,
     |                outcast = set([]),
     |                remap = dict(),
     |                type = int,
     |                values = set([3, 4, 5, 6, 7]),
     |            ),
     |            colour = dict(
     |                access = 'rxx',
     |                alias = set([]),
     |                default = None,
     |                optional = False,
     |                outcast = set([]),
     |                remap = dict(
     |                    lightgreen = 'green',
     |                ),
     |                values = set(['green', 'lightgreen']),
     |            ),
     |            producer = dict(f
     |                access = 'rxx',
     |                alias = set([]),
     |                default = 'Jacques',
     |                optional = True,
     |                outcast = set([]),
     |                remap = dict(),
     |                values = set([]),
     |            ),
     |        ),
     |        bind = [],
     |        info = 'Forbidden Fruit',
     |        only = dict(),
     |        priority = dict(
     |            level = footprints.priorities.PriorityLevel('DEFAULT'),
     |        ),
     |    )
     |
     |  Method resolution order:
     |      GrannySmith
     |      fruits.Apple
     |      fruits.Fruit
     |      footprints.FootprintBase
     |      __builtin__.object
     |
     |  Data descriptors defined here:
     |
     |  size
     |      Undocumented footprint attribute
     |
     |  colour
     |      Undocumented footprint attribute
     |
     |  producer
     |      Undocumented footprint attribute
     |
     |  ----------------------------------------------------------------------
     |  Methods inherited from footprints.FootprintBase:
     |
     | ...

Many class or object methods return partial information on the footprint,
allowed values, and so on. See the online documentation for the
:class:`~footprints.FootprintBase` class.

Collector methods
-----------------

Filter mechanisms, eliminating collector elements, managing instances, etc.

.. note:: Documentation to complete...

==============
Other features
==============

Internally the footprints package relies on some utilities or implements some
design patterns that it is quite possible to use outside
:class:`footprints.FootprintBase` classes.

This includes the system of loggers, observers, a class-factory by *tag*... these
are hosted in the independent :mod:`bronx` package.

Finally, a descriptive model expansion mechanism is used (see below).

Expansion mechanism
-------------------

Since class fingerprint resolution is based on a key/value list description, it
is more than reasonable to imagine that some expansion mechanisms of said list
according to some of the proposed values can be performed.

The :func:`footprints.util.expand` function takes care of this very useful job,
possibly in conjunction with :func:`bronx.stdtypes.date.timeintrangex`.

The first expansion that we can think of is naturally that of the iterable
Python base types :func:`list`, :func:`tuple`, :func:`set`, and to a certain
extent :func:`dict`.

This is also the case for strings containing “ranges”, or containing values
separated by commas, and even containing indications of *globbing*!

.. seealso::

   more detail is given in the :func:`footprints.util.expand` function
   documentation.

==========
Conclusion
==========

.. seealso::

    The real strength of the thing is that the choice is made in places that we
    do not anticipate a priori!

==================
Indices and tables
==================

.. toctree::
    :hidden:

    footprints_fr
    footprints_auto

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
