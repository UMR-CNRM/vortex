.. _footprints_doc_fr:

*************************
Le package « footprints »
*************************

Une arlésienne de la programmation objet est que l'on aimerait bien le plus souvent ne pas avoir
à caractériser précisément l'objet que l'on veut utiliser pour remplir un certain rôle.
À tout le moins on ne voudrait pas à avoir à spécifier la classe qu'on instanciera pour obtenir ledit objet.
Il nous suffit le plus souvent de penser que tel ou tel objet réunit certaines qualités
ou être capable de réaliser telle ou telle action. On trouve souvent comme boutade
dans la littérature de programmation objet qu'un bon code objet est un code
où on ne manipule que des classes et jamais des objets.

C'est un peu ce rôle de dispensateur d'objets, sur la base de la simple description
de caractéristiques de classe, que le package :mod:`footprints` se propose d'assumer.
C'est cela, et un peu plus, puisqu'il va permettre (à ce stade de la présentation il faut un peu faire acte de foi)
d'assurer la maintenabilité (dans le temps, ou vis-à-vis de modifications de comportement
de telles ou telles « classes d'objets » qui ne s'imposeraient pas
immédiatement à l'esprit de leur créateur au moment de leur conception)
et surtout l'extensibilité de tout ensemble logiciel qui prendrait le package « footprints » comme fondement
de son développement. Cerise sur le gâteau, nous verrons qu'il assure même l’interopérabilité
entre différents ensembles logiciels, pourvu qu'ils respectent des conventions purement formelles.

L'idée en est très simple. C'est une variante un tantinet élaborée du *Pattern* de la fabrique.
Au lieu de décrire précisément un objet dans toutes ses caractéristiques (et notamment en fournissant sa classe),
on va prendre le problème à l'envers et tenter de répondre à la question : quelle classe serait susceptible
de s'instancier dans un objet qui aurait des caractéristiques compatibles avec celles dont j'ai connaissance a priori ?

Dit autrement, vous vous baladez dans un chemin forestier, et vous voyez des bouts d'empreintes mélangées,
dans la boue par exemple, ou parfois masquées par une flaque, ou des feuilles d'arbre arrachées, etc.,
et vous vous demandez : « quelle est donc la ou les bestiole-s qui ont pu laisser de telles empreintes » ?
Et si jamais il y a au moins une réponse à cette question eh bien, j'aimerai la connaître et en disposer
librement pour par exemple, évaluer ses autres caractéristiques (telle profondeur d'empreintes peut donner
une indication de poids par exemple, etc.) ou lui faire faire telle ou telle action (on dit : *méthode*).

Toute analogie ayant ses limites, jouons plutôt un peu avec ce package.

============
Premiers pas
============

On peut considérer ce composant de base sous différents angles :
celui de l'utilisateur de couches supérieures de la boîte à outils
qui ne s'apercevra pas de son existence (si tout va bien), ou celui du développeur
qui voudra pleinement profiter de l'extensibilité offerte par l'usage des « footprints » comme fabrique objet.
Et entre les deux, toute une variété d'utilisations. À vous de faire le tri !

L'importation du package n'active pour le moment absolument rien::

    >>> import footprints

Ce que va fondamentalement permettre le package :mod:`footprints` c'est de grouper des classes
selon une logique d'utilisation qui sera propre à chaque concepteur, ou utilisateur.
Mais pas n'importe quelle classe, des classes qui dériveront d'un type de base
nommé :class:`footprints.FootprintBase`.

On dira alors que ces classes sont « collectées »… par des « collectors », qui sont des sortes de catalogues.
On peut demander au package :mod:`footprints` quelle est la liste des classes collectées,
ou bien  demander au module :mod:`footprints.collectors` la liste des catalogues en « activité ».
Si nous n'avons rien fait d'autre que d'importer le package principal, ces listes sont vides bien entendu ::

    >>> footprints.collected_classes()
    set([])
    >>> footprints.collectors.keys()
    []

Histoire de gagner du temps par la suite, nous adopterons la convention suivante::

    >>> import footprints as fp

Notre exemple fil rouge consistera à manipuler quelques fruits. Il sera toujours temps
de faire de la prévision numérique plus tard. Deux variables de classe suffiront à caractériser
des classes de type footprint (caractéristiques qui se transmettront bien entendu par héritage):
le ou les noms des collecteurs auxquelles elles souhaitent contribuer, et leur empreinte.
Pour illustrer la chose, définissons une classe de base de type ``Fruit`` dans un module ``fruits``.

.. code-block:: python

    class Fruit(fp.FootprintBase):
        _collector = ('fruit',)
        _footprint = dict(
            info = 'Fruit defendu',
            attr = dict(
                couleur = dict(),
            )
        )

Si l'on interroge maintenant la liste des noms de collecteurs, celle-ci n'est plus vide::

    >>> fp.collectors.keys()
    ['fruit']
    >>> fp.collected_classes()
    set([<class 'fruits.Fruit'>])

Nous pourrions récupérer ce collecteur de fruits, et lui demander, par exemple un fruit de couleur verte::

    >>> cf = fp.collectors.get(tag='fruit')
    >>> print cf
    <footprints.collectors.Collector object at 0x7fb488f77950>
    >>> print cf.tag
    fruit
    >>> p = cf.load(couleur='verte')
    print p
    <fruits.Fruit object at 0x7fb488f77d10 | footprint=1>

Avec la méthode :meth:`~footprints.collectors.Collector.load` du collecteur nous avons récupéré un fruit
dont l'empreinte est constituée par un attribut, sa couleur, qui semble lui coller à la peau::

    >>> print p.couleur
    verte
    >>> p.couleur = 'rouge'
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/home/sevault/git-dev/vortex/site/footprints/access.py", line 93, in __set__
        raise AttributeError('Read-only attribute [' + self._attr + '] (write)')
    AttributeError: Read-only attribute [couleur] (write)
    >>> del p.couleur
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/home/sevault/git-dev/vortex/site/footprints/access.py", line 96, in __delete__
        raise AttributeError('Read-only attribute [' + self._attr + '] (delete)')
    AttributeError: Read-only attribute [couleur] (delete)

C'est déjà pas mal (en étant très bienveillant). Mais franchement ça ne casse pas trois pattes à un canard.
Nous pourrions tout d'abord nous dire que c'est dommage de pouvoir instancier une classe comme ``Fruit``.
De toute évidence, c'est une classe abstraite, alors autant le dire tout de suite. Reprenons notre exemple
de zéro ou presque et en définissant ``Fruit`` comme abstraite et en créant deux classes bien réelles,
les pommes et les fraises, et pas de scoubidoubidouwouah::

    class Fruit(fp.FootprintBase):
        _collector = ('fruit',)
        _abstract  = True
        _footprint = dict(
            info = 'Fruit defendu',
            attr = dict(
                couleur = dict(),
            )
        )

    class Pomme(Fruit):
        _footprint = dict(
            attr = dict(
                couleur = dict(
                    values = ['verte', 'jaune', 'rouge']
                )
            )
        )

    class Fraise(Fruit):
        _footprint = dict(
            attr = dict(
                couleur = dict(
                    values = ['rouge']
                )
            )
        )

Plutôt que de continuer à demander un collecteur explicitement comme nous l'avons fait précédemment,
ce qui est quelque peu laborieux, nous allons utiliser un autre raccourci du package :mod:`footprints`,
donné par un proxy permettant d'accéder dynamiquement à tous les collecteurs qui ont été créés
à un moment ou à un autre au gré des chargements de modules (nous reviendrons sur cet aspect capital)::

    >>> print fp.proxy
    <footprints.proxies.FootprintProxy object at 0x7f142c28b590>
    >>> fp.proxy.fruits
    <footprints.collectors.Collector object at 0x7f142c28bad0>

Les collectors sont des objets appelables, qui renvoient la liste des classes susceptibles de s'instancier dans cette catégorie::

    >>> fp.proxy.fruits()
    [<class 'fruits.Pomme'>, <class 'fruits.Fraise'>]

Miracle ! Comme on l'espérait, il n'y a que deux sortes de fruits collectés: ``Pomme`` et ``Fraise``.
Demandons maintenant un fruit quelconque de couleur verte::

    >>> x = fp.proxy.fruit(couleur='verte')
    >>> print x
    <fruits.Pomme object at 0x7f142c00d390 | footprint=1>

Eh oui ! C'est une pomme ! Et si je demande un fruit de couleur jaune ? Résultat::

    >>> y = fp.proxy.fruit(couleur='jaune')
    >>> print y
    <fruits.Pomme object at 0x7f142c00d450 | footprint=1>

Et pour un fruit de couleur bleue::

    >>> b = fp.proxy.fruit(couleur='bleue')
    # [2015/16/06-16:12:21][footprints.collectors][pickup:0151][WARNING]: No 'fruit' found in description
        dict(
            couleur = 'bleue',
            fruit = None,
        )

    Report Footprint-Fruit:

        fruits.Fraise
            couleur    : {'args': 'bleue', 'why': 'Not in values'}

        fruits.Pomme
            couleur    : {'args': 'bleue', 'why': 'Not in values'}

Nous obtenons un rapport d'instanciation qui nous indique clairement pourquoi aucune des classes
candidates ne peut être sélectionnée, et pour une bonne raison visiblement (sauf si vous raffolez des fraises bleues).

À ce stade très rudimentaire de l'exposition du mécanisme d'instanciation par « footprints »,
nous pouvons déjà faire quelques remarques :

  * à aucun moment il n'est nécessaire de faire d'hypothèse sur le nombre de classes éligibles ;
  * la connaissance *a priori* des attributs qui correspondent (ou pas) à telle ou telle classe est facultative, le mécanisme de résolution des valeurs acceptables, fera le tri naturellement ;
  * il a suffit qu'une classe définisse une valeur à sa variable de classe :envvar:`_collector` pour qu'un tel collecteur existe ;
  * les classes peuvent être définies n'importe où dans l'arborescence de votre package, ou dans un package extérieur que vous importeriez pour qu'automatiquement les classes héritant de footprints.FootprintBase soient collectées.

Ces deux derniers aspects sont au fondement de l'extensibilité de tout code s'appuyant sur les footprints, et donc... de VORTEX.

=================
En cas de conflit
=================

Tout ceci est bel et bon, me direz-vous, mais que se passe-t-il si l'on demande un fruit rouge ? Eh bien, voici::

    >>> r = fp.proxy.fruit(couleur='rouge')
    # [2015/16/06-16:35:48][footprints.collectors][find_best:0203][WARNING]: Multiple fruit candidates
        dict(
            couleur = 'rouge',
        )
    # [2015/16/06-16:35:48][footprints.collectors][find_best:0207][WARNING]: no.1 in.1 is <class 'fruits.Pomme'>
    # [2015/16/06-16:35:48][footprints.collectors][find_best:0207][WARNING]: no.2 in.1 is <class 'fruits.Fraise'>

Vous récoltez un magnifique avertissement car plusieurs choix sont possibles. Ce n'est pas forcément un souci.
Dans la vie courante, si vous demandez une chaise, c'est probablement pour vous assoir,
peu importe qu'elle soit en plastique ou en bois. Ici dans notre exemple-jeu, la confusion entre couleur extérieure du fruit et de sa
chair est plus délicate. Mais nous ferons avec. La question est : que faire si il faut pouvoir distinguer. Ou
plus exactement et plus généralement : selon quels critères des empreintes compatibles seront-elles distinguées ?

Les empreintes usent dans ce cas d'une heuristique assez intuitive : le tri s'opère en fonction du niveau
de priorité et du nombre d'attributs reconnus dans l'empreinte.

Dans le cas de nos pommes et fraises, telles que les classes ont été définies, il n'y a pas de distinguo
en terme de priorité et elles ont toutes deux un seul attribut. Ce serait bien d'étoffer un peu tout cela.

Niveaux de priorité
-------------------

Le package :mod:`footprints` définit par défaut un niveau de priorité pour chaque objet à empreinte.

Regardons notre pomme par exemple::

    >>> print x.footprint_level()
    DEFAULT

Si on y regarde de plus près, le module :mod:`footprints.priorities` a défini un jeu de priorités
nommé :envvar:`top` avec quelques niveaux par défaut::

    >>> print fp.priorities.top
    <footprints.priorities.PrioritySet object at 0x7f142c275f90>
    >>> print fp.priorities.top.levels
    ('NONE', 'DEFAULT', 'TOOLBOX', 'DEBUG')

accessibles directement, et ordonnés les uns par rapport aux autres::

    >>> top = fp.priorities.top
    >>> print top.DEFAULT
    <footprints.priorities.PriorityLevel object at 0x7f142c2810d0>
    >>> print top.TOOLBOX
    <footprints.priorities.PriorityLevel object at 0x7f142c281110>
    >>> top.DEFAULT > top.TOOLBOX
    False

Toutes les opérations imaginables sur un tel jeu de priorités sont évidemment fournies: insertions, permutations,
éliminations, etc. Dans le contexte vortexien par exemple, nous commençons par cette simple séquence de modification
de l'ordre des priorités, dès les footprints chargés::

    >>> fp.priorities.set_before('debug', 'olive', 'oper')
    >>> top.levels
    ('NONE', 'DEFAULT', 'TOOLBOX', 'OLIVE', 'OPER', 'DEBUG')

On pourrait ainsi imaginer que les fraises ont une priorité plus haute que les pommes, car elles se
conservent moins longtemps. La déclaration du footprint de la classe serait alors::

    class Fraise(Fruit):
        _footprint = dict(
            attr = dict(
                couleur = dict(
                    values = ['rouge']
                )
            ),
            priority = dict(
                level = fp.priorities.top.TOOLBOX
            ),
        )

Retournons à notre sélection de départ::

    >>> r = fp.proxy.fruit(couleur='rouge')
    # [2015/16/06-17:05:01][footprints.collectors][find_best:0203][WARNING]: Multiple fruit candidates
      dict(
          couleur = 'rouge',
      )
    # [2015/16/06-17:05:01][footprints.collectors][find_best:0207][WARNING]: no.1 in.1 is <class 'fruits.Fraise'>
    # [2015/16/06-17:05:01][footprints.collectors][find_best:0207][WARNING]: no.2 in.1 is <class 'fruits.Pomme'>

Il y a toujours un message d'avertissement car, de fait, il y a plusieurs fruits candidats, mais la fraise gagnera
immanquablement la compétition !

Mais nous avions dit également que le nombre d'attributs correspondant à une empreinte donnée serait pris en compte.
Ceci n'est possible que si l'on peut ou non renseigner un attribut. Autrement dit, si une classe dispose d'attributs
optionnels dans son footprint.

Attributs optionnels
--------------------

Nous allons maintenant doter la pomme d'un attribut optionnel, à savoir le nom du producteur. Les fraises, c'est bien connu,
sont produites en Espagne, hors sol, par des sociétés anonymes, et n'auront donc pas un tel attribut. La déclaration complète
a donc maintenant cette allure::

    class Pomme(Fruit):
        _footprint = dict(
            attr = dict(
                couleur = dict(
                    values = ['verte', 'jaune', 'rouge']
                ),
                producteur = dict(
                    optional = True,
                    default = 'Jacques',
                )
            )
        )

Que se passe-t-il au moment de choisir un fruit de couleur rouge ? Ceci::

    >>> r = fp.proxy.fruit(couleur='rouge', producteur='marcel')
    # [2015/16/06-17:14:34][footprints.collectors][find_best:0203][WARNING]: Multiple fruit candidates
        dict(
            couleur = 'rouge',
            producteur = 'marcel',
        )
    # [2015/16/06-17:14:34][footprints.collectors][find_best:0207][WARNING]: no.1 in.1 is <class 'fruits.Fraise'>
    # [2015/16/06-17:14:34][footprints.collectors][find_best:0207][WARNING]: no.2 in.2 is <class 'fruits.Pomme'>

La résolution se faisant d'abord par niveau de priorité, c'est toujours une fraise qui est sélectionnée prioritairement.

Si nous revenions à deux catégories de fruits de priorité identique (hypothèse pour la suite du tutoriel, sauf
mention contraire), nous aurions alors::

    >>> r = fp.proxy.fruit(couleur='rouge', producteur='Marcel')
    # [2015/16/06-17:21:10][footprints.collectors][find_best:0203][WARNING]: Multiple fruit candidates
        dict(
            couleur = 'rouge',
            producteur = 'Marcel',
        )
    # [2015/16/06-17:21:10][footprints.collectors][find_best:0207][WARNING]: no.1 in.2 is <class 'fruits.Pomme'>
    # [2015/16/06-17:21:10][footprints.collectors][find_best:0207][WARNING]: no.2 in.1 is <class 'fruits.Fraise'>

Et là, la pomme est immanquablement sélectionnée car elle a deux attributs qui correspondent à l'empreinte.
On constate bien entendu que l'on dispose maintenant de l'attribut "producteur" pour la pomme en question::

    >>> print r.producteur
    Marcel

Dans la mesure où il est optionnel, le "producteur" ne se retrouve pas forcément dans l'empreinte. La valeur
par défaut est dans ce cas affectée à l'attribut::

    >>> p = fp.proxy.fruit(couleur='verte')
    >>> print p.producteur
    Jacques

========
Héritage
========

En jetant dès maintenant un coup d'œil par dessus notre épaule, nous pouvons voir que les classes que nous
voulons rendre éligible au mécanisme d'instanciation par empreintes doivent donc hériter d'une classe de base
nommée :class:`footprints.FootprintBase` et définir leur empreinte via la variable de classe **_footprint**.

En fait même si nous avons défini ce **_footprint** comme une structure python de base (dict),
il est automatiquement transformé en un objet de classe :class:`footprints.Footprint`. lors de la création
de la classe par l'interpréteur python (en fait par la méta-classe utilisée pour instancier cette classe, mais
cela nous emmènerait un peu trop profondément dans les soutes magiques du package).

En trichant quelque peu avec les règles d'accès aux attributs "cachés" de la classe (ie: précédés par un underscore),
c'est quelque chose que l'on peut aisément vérifier::

    >>> fruits.Pomme
    <class 'fruits.Pomme'>
    >>> fruits.Pomme._footprint
    <footprints.Footprint object at 0x7f9ef0bf19d0>

La façon propre de récupérer l'objet footprint associé à une classe est d'utiliser
la méthode de classe :meth:`~footprints.FootprintBase.footprint_retrieve`::

    >>> fruits.Pomme.footprint_retrieve()
    <footprints.Footprint object at 0x7f9ef0bf19d0>

Nous verrons plus tard les méthodes qui s'appliquent à cet objet pour les plus curieux. Mais ce qui nous intéresse
c'est de savoir comment cette double intrication (la classe et son objet footprint) se comporte en cas d'héritage.

Héritage de classe
------------------

En terme d'héritage pythonesque classique, il n'y a rien de neuf apporté par les classes dérivées
de :class:`footprints.FootprintBase` : en l'absence de toute nouvelle redéfinition de leur footprint,
elles "récupèrent" un footprint identique à celui de la classe parente.

**Attention:** identique signifie qu'il en a toutes les qualités et propriétés mais sans être le même objet !
Comme on peut le constater dans ce court exemple::

    >>> class GrannySmith(fruits.Pomme):
            pass
    >>> GrannySmith.footprint_retrieve()
    <footprints.Footprint object at 0x7f9eedde04d0>

Par construction, une telle classe a donc la même empreinte que sa classe parente, et elle sera donc en toute
occasion "concurrente" de sa classe parente dans les mécanismes d'instanciation qui suivront. Pourquoi pas. On
peut par exemple s'intéresser uniquement à la redéfinition ou l'extension de ses méthodes de classe.
Mais il est bien plus probable que l'on souhaite plutôt modifier son empreinte dans le même processus d'héritage.

Surcharge du footprint
----------------------

C'est là que la fabrique objet prend tout son sel. Dans la définition d'une classe fille il va être possible
de surcharger le footprint de la classe parente, uniquement pour ce qui a besoin de l'être, ce qui n'exclut pas
bien entendu d'être redondant et de redéfinir à l'identique une caractéristique du footprint (pour blinder la chose
ou tout simplement parce que l'on n'a aucune certitude sur le détail du footprint de la classe dont on hérite).

Reprenons notre belle Granny Smith, que nous codons dans un module nommé :file:`verger.py` par exemple::

    class GrannySmith(fruits.Pomme):
        _footprint = dict(
            attr = dict(
                couleur = dict( values = ['verte'] ),
                calibre = dict( values = range(3, 8) ),
            ),
        )

Nous pouvons imaginer maintenant que tout gros fruit de couleur verte sera une Granny Smith. Vérifions::

    >>> import verger
    >>> fp.proxy.fruits()
    [<class 'verger.GrannySmith'>, <class 'fruits.Fraise'>, <class 'fruits.Pomme'>]
    >>> fp.proxy.fruit(couleur='verte', calibre=7)
    <verger.GrannySmith object at 0x7fd427e5a610>

Et si vous êtes un peu perdu, il est toujours possible de demander au collecteur de fruits de vous dresser
la carte des attributs possibles::

    >>> fp.proxy.fruits.show_attrmap()
     * calibre [optional]:
         GrannySmith            + verger
                                 | values = 3, 4, 5, 6, 7

     * couleur:
         Fraise                 + fruits
                                 | values = rouge
         GrannySmith            + verger
                                 | values = verte
         Pomme                  + fruits
                                 | values = jaune, verte, rouge

     * producteur [optional]:
         GrannySmith            + verger
         Pomme                  + fruits

Il y a donc une sorte de "merge" des footprints dans l'ordre d'héritage des classes. Ce qui est à la fois totalement
intuitif et très puissant. Ajoutons enfin que les empreintes peuvent être définies directement par un objet ou une liste
d'objets. Construisons par exemple une voiture comme assemblage d'un moteur et d'une carrosserie::

    traction = fp.Footprint(
        attr = dict(
            chdyn = dict(
                values = [70, 90, 110, 125],
            ),
            animal = dict(
                type = bool,
                optional = True,
                default = False,
            ),
        )
    )

    habitacle = fp.Footprint(
        attr = dict(
            comfort = dict(
                values = ['cosy', 'correct', 'rudimentaire'],
                optional = True,
                default = 'correct',
            ),
        )
    )

    class Voiture(fp.FootprintBase):
        _abstract = True
        _collector = ('voiture',)
        _footprint = [traction, habitacle]

    class Charette(Voiture):
        _footprint = dict(
            attr = dict(
                animal = dict(
                    values = [True],
                ),
                comfort = dict(
                    default = 'rudimentaire',
                )
            )
        )

Ce qui donnerait par exemple::

    >>> fp.proxy.voitures()
    [<class 'voitures.Charette'>]
    >>> c = fp.proxy.voiture(chdyn=70, animal=True)
    >>> c
    <voitures.Charette object at 0x7f9a257b1150>
    >>> c.animal
    True
    >>> c.comfort
    'rudimentaire'

=========================================
Caractéristiques générales des empreintes
=========================================

Nous allons maintenant passer en revue les différentes caractéristiques qui permettent d'affiner les définitions d'empreintes.

Typage
------

On considère qu'un attribut est par défaut une chaîne de caractères, mais cela peut être absolument n'importe
quelle autre classe, que ce soit un type de base de python ou une classe utilisateur.

Imaginons que nous voulions maintenant, pour chaque fruit, lui attribuer un calibre, représenté par un entier
compris en 1 et 6, valant par défaut 2. Il suffit rétroactivement de modifier la classe de base de la façon
suivante::

    class Fruit(fp.FootprintBase):
        _collector = ('fruit',)
        _abstract  = True
        _footprint = dict(
            info = 'Fruit defendu',
            attr = dict(
                couleur = dict(),
                calibre = dict(
                    type = int,
                    optional = True,
                    default = 2,
                    values = range(1, 7),
                )
            ),
        )

Reprenons ce que nous savons être une pomme::

    >>> p = fp.proxy.fruit(couleur='verte')
    >>> print p.calibre
    2

Essayons maintenant une autre valeur numérique exprimée comme basestring::

    >>> p = fp.proxy.fruit(couleur='verte', calibre='04')
    >>> print p.calibre
    4

La conversion de type (ou *cast*), du moment qu'elle est valide (au sens de ce que peut accepter le constructeur de la classe
spécifiée comme type d'attribut), se fait automatiquement. Sinon, on échoue::

    >>> x = fp.proxy.fruit(couleur='verte', calibre='rectangle')
    # [2015/16/06-19:36:39][footprints.collectors][pickup:0151][WARNING]: No 'fruit' found in description
        dict(
            calibre = 'rectangle',
            couleur = 'verte',
            fruit = None,
        )

    Report Footprint-Fruit:

        fruits.Fraise
            couleur    : {'args': 'verte', 'why': 'Not in values'}
            calibre    : {'args': ('int', 'rectangle'), 'why': 'Could not reclass'}
            calibre    : {'args': None, 'why': 'Not in values'}

        fruits.Pomme
            calibre    : {'args': ('int', 'rectangle'), 'why': 'Could not reclass'}
            calibre    : {'args': None, 'why': 'Not in values'}

Valeurs autorisées
------------------

Nous avons déjà eu de multiples occasions de préciser les valeurs acceptables pour un attribut d'empreinte
avec l'élément **values**. C'est particulièrement commode pour distinguer entre familles d'objets, puisque
toute valeur proposée qui ne correspondra pas à la plage de valeurs autorisées ne permettra pas d'instancier
cette classe. Cela peut aussi permettre
de coder des méthodes spécifiques pour telles ou telles classes, sans truffer son code de "if".

Mais cela peut permettre aussi de particulariser temporairement un traitement (à des fins de mise au point
ou de déverminage par exemple).

La seule chose complémentaire à savoir est que les valeurs spécifiées sont automatiquement retypées dans le type
spécifié pour l'attribut courant. Dans le cas du calibre par exemple, nous aurions pu donner des valeurs obligatoires.

Valeurs prohibées
-----------------

Tout aussi commode, il est possible de spécifier les valeurs absolument prohibées. Dit autrement, un objet de cette
classe ne pourrait pas avoir laissé une empreinte de cette ou de ces valeurs. La classe n'est donc plus éligible
pour le processus d'instanciation. C'est la clé **outcast** qui permet de spécifier les valeurs prohibées.
Tout comme les valeurs associées à la clé **values**, elles sont automatiquement retypées dans le type spécifié pour
l'attribut courant.

Voici un exemple avec un fruit qui ne pourrait raisonnablement pas pousser sous certaines latitudes::

    class Ananas(Fruit):
        _footprint = dict(
            attr = dict(
                origine = dict(
                    outcast = ['Ecosse', 'Irlande'],
                )
            )
        )

Et vérifions::

    >>> a = fp.proxy.fruit(couleur='orange', origine='Ecosse')
    # [2015/17/06-15:25:17][footprints.collectors][pickup:0151][WARNING]: No 'fruit' found in description
        dict(
            couleur = 'orange',
            fruit = None,
            origine = 'Ecosse',
        )

    Report Footprint-Fruit:

        fruits.Ananas
            origine    : {'args': 'Ecosse', 'why': 'Outcast value'}

        fruits.Fraise
            couleur    : {'args': 'orange', 'why': 'Not in values'}

        fruits.Pomme
            couleur    : {'args': 'orange', 'why': 'Not in values'}

Changement de valeur à la volée
-------------------------------

Il peut être utile de repositionner une valeur, soit que l'on veuille permettre une certaine approximation, soit que l'on
veuille restreindre les valeurs réellement manipulées par la suite par les différents objets instanciées, tout en laissant
une certaine latitude de choix à l'utilisateur. Il faut néanmoins déclarer ces valeurs "alternatives"
dans les valeurs autorisées (si il y en a qui sont définies explicitement).

Reprenons par exemple le cas des Granny Smith::

    class GrannySmith(fruits.Pomme):
        _footprint = dict(
            attr = dict(
                calibre = dict( values = range(3, 8) ),
                couleur = dict(
                    values = ['verte', 'vert'],
                    remap  = dict(vert = 'verte'),
                ),
            ),
        )

Nous obtenons::

    >>> p = fp.proxy.fruit(couleur='vert', calibre=5)
    >>> p.fullname()
    'verger.GrannySmith'
    >>> p.couleur
    'verte'

Et nous pouvons vérifier qu'une "simple" pomme ne faisait pas l'affaire::

    >>> fp.proxy.fruits.report_whynot('fruits.Pomme')
    {'fruits.Pomme': {'couleur': {'args': 'vert', 'why': 'Not in values'}}}

Inutile d'épiloguer plus longuement sur l'incroyable souplesse que permet cette fonctionnalité.

Alias de noms d'attributs
-------------------------

Une autre façon de particulariser une empreinte est d'autoriser différentes façons de nommer un attribut identique.
Dans le cas de nos fruits, on aurait pu imaginer que l'aspect soit un synonyme pour la couleur par exemple, et le
mettre dans la classe générique de base. Dans ce cas, il ne s'agirait que d'une façon commode de nommer une qualité
de tous les fruits. C'est déjà quelque chose de très pratique, ne serait-ce qu'en terme d'évolution d'un ensemble logiciel
dont on peut au fur et à mesure permettre les associations de noms.

Mais cela s'avère aussi une façon élégante de discriminer entre empreintes identiques. Imaginons que cet alias de nom
ne soit posé que sur les fraises. Seule cette classe de fruit serait alors éligible si nous utilisons l'attribut *aspect*.

.. code-block:: python

    class Fraise(Fruit):
        _footprint = dict(
            attr = dict(
                couleur = dict(
                    values = ['rouge', 'verte'],
                    alias = ('aspect', 'coloration'),
                )
            ),
        )

Nous vérifions que cela ne crée pas un nouvel attribut::

    >>> f = fp.proxy.fruit(aspect='rouge')
    >>> f.fullname()
    'fruits.Fraise'
    >>> f.aspect
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    AttributeError: 'Fraise' object has no attribute 'aspect'
    >>> f.couleur
    'rouge'

Descripteurs d'attributs
------------------------

Nous avons constaté plus haut qu'il n'est pas possible de repositionner la valeur d'un attribut faisant partie
de l'empreinte utilisée lors du processus d'instanciation. Ceci est motivé par le raisonnement suivant: si telle
ou telle classe a "gagné" lors de ce processus de sélection, elle le doit aux valeurs spécifiques utilisées à
ce moment. Il n'est donc pas raisonnable de les changer. De nouvelles valeurs auraient peut-être amené l'instanciation
d'une autre classe.

Néanmoins, il ne faut pas être trop dogmatique. Certaines valeurs d'attributs sont tellement larges, ou simplement
non restreinte par la clé *values*, que l'on peut s'autoriser à les modifier.

En fait, pour chaque attribut de l'empreinte, un descripteur (ou accesseur) est défini dans le code python (il n'est
pas obligatoire de comprendre cela, surtout si vous n'avez pas de notion des *descriptors* de python). Le package
footprints ayant décidé de vous rendre la vie facile, la chose va se résumer à donner une valeur intuitive à une clé
nommée *access*. Les valeurs possibles sont:

    * 'rxx' (c'est le défaut : read-only)
    * 'rwx' (read - write)
    * 'rwd' (read - write - delete)

et leur déclinaison avec références "molles" (auquel cas les valeurs stockées dans les attribues sont des *weakref*:

    * 'rxx-weak' (c'est le défaut : read-only)
    * 'rwx-weak' (read - write)
    * 'rwd-weak' (read - write - delete)

On peut ainsi imaginer que des ananas d'Irlande changent d'origine lors de leur passage en douane, histoire
de se conformer aux exigences locales::

    class Ananas(Fruit):
        _footprint = dict(
            attr = dict(
                origine = dict(
                    outcast = ['Ecosse', 'Irlande'],
                    access = 'rwx',
                )
            )
        )

Et voici la fraude::

    >>> a = fp.proxy.fruit(couleur='orange', origine='Chine')
    >>> a.origine
    'Chine'
    >>> a.origine = 'Costa Rica'
    >>> print a.origine
    Costa Rica

Mais nous respectons néanmoins l'empreinte de la classe::

    >>> a.origine = 'Ecosse'
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/home/sevault/git-dev/vortex/site/footprints/access.py", line 54, in __set__
        raise ValueError('Value {0:s} excluded from range {1:s}'.format(str(value), str(list(fpdef['outcast']))))
    ValueError: Value Ecosse excluded from range ['Irlande', 'Ecosse']

Ce serait vrai aussi pour les valeurs autorisées, le type de l'attribut, etc.

Arguments pour le type d'attribut
---------------------------------

Par souci d'exhaustivité, signalons la dernière clé possible dans la description d'un attribut d'empreinte, à savoir
les arguments qui seront passés lors du typage automatique de la valeur. Nous entrons là dans des subtilités dont
il est difficile de percevoir d'emblée l'utilité, mais disons pour faire simple, que si nous "typons" automatiquement
tout attribut, cela signifie que nous appelons le constructeur pour un type donné (i.e. une classe donnée), et qu'il
serait dommage de s'interdire de pouvoir passer au dernier moment certains attributs. Nous avons de très rares cas
de figure dans le VORTEX... que nous commenterons... ou pas !

Cette option doit se présenter sous la forme d'un dictionnaire, comme dans cet exemple d'un imaginaire module de flacons::

    class Volume(int):
        def __new__(cls, value, unit='ml'):
            obj = int.__new__(cls, value)
            obj._unit = unit
            return obj
        def __str__(self):
            return '{0:d}{1:s}'.format(self, self._unit)

    class Contenant(fp.FootprintBase):
        _abstract = True
        _collector = ('contenant',)
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

Et à l'usage::

    >>> c = fp.proxy.contenant(volume=50)
    >>> c.fullname()
    'flacons.Carafe'
    >>> c.volume
    50
    >>> print c.volume
    50cl

Classe ou objet
---------------

Et que se passe-t-il quand le type attendu d'un attribut est non un objet, mais une classe ? Bien entendu, en python,
les classes elles-mêmes sont des objets. Mais il faut pourtant pouvoir distinguer entre un type fourni dans le but
d'instancier une valeur d'attribut et le fait que l'on veuille que l'attribut lui-même reste une classe. Ce n'est pas une
rareté dès que l'on pense en terme de collaboration de classes, ou de composition. Moralité, une clé optionnelle est
évaluée lors de la résolution des footprints, la clé *isclass*.

Si elle est positionnée à *vrai*, alors on ne cherche pas à instancier la valeur de l'attribut dans la classe donnée
par la clé *type*, mais on vérifie simplement que l'attribut est une sous-classe de ce type.

.. note:: Merci d'ajouter des exemples ?

====================
Affiner la sélection
====================

En plus des éléments *attr*, *info* et *priority* que nous avons croisés plus haut, il y a un autre élément
de caractérisation de l'empreinte qui joue un rôle important dans le mécanisme de résolution des footprints.
Il s'agit du composant *only* du footprint.

Utiliser *only* par valeur exacte
---------------------------------

Il peut, bien entendu, ne pas être renseigné, et c'était le cas dans tous nos exemples précédents. Mais quand
il l'est, cela permettra de filtrer les classes candidates à l'instanciation en fonction de paramètres
déjà définis dans le footprint ou que l'on pourrait qualifier d' "extérieurs" aux caractérisations
de l'empreinte proprement dite, et déclarés dans les paramètres par défaut.

La sélection n'a de sens que quand la résolution est déjà un succès, histoire de vérifier si d'autres
critères plus restrictifs (ou plus dynamiques) ne s'appliquent pas.

Nous allons prendre un exemple simple : les récoltes 2001 et 2007 virent poindre
dans les vergers de nos campagnes des pommes bleues. Mais ces années seulement::

    class Zorg(fruits.Pomme):
        _footprint = dict(
            attr = dict(
                couleur = dict(
                    values = ['bleue'],
                ),
            ),
            only = dict(
                recolte = (2001, 2007),
            )
        )

Si l'on ne change rien à nos tentatives précédentes, peu de chance de récupérer une pomme bleue::

    >>> fp.proxy.fruit(couleur='bleue')
    # [2015/17/06-20:02:00][footprints.collectors][pickup:0151][WARNING]: No 'fruit' found in description
        dict(
            couleur = 'bleue',
            fruit = None,
        )

    Report Footprint-Fruit:

        fruits.Ananas
            origine    : {'why': 'Missing value'}

        fruits.Fraise
            couleur    : {'args': 'bleue', 'why': 'Not in values'}

        fruits.Pomme
            couleur    : {'args': 'bleue', 'why': 'Not in values'}

        verger.GrannySmith
            couleur    : {'args': 'bleue', 'why': 'Not in values'}
            calibre    : {'args': 2, 'why': 'Not in values'}

        verger.Zorg
            recolte    : {'only': 'No value found', 'args': 'recolte'}

Définissons maintenant, pour l'ensemble du package footprints, une date de récolte par défaut
(le mécanisme en sera expliqué plus tard),
mais qui ne corresponde pas à notre filtre *only*::

    >>> fp.setup.defaults(recolte=2014)
    >>> fp.proxy.fruit(couleur='bleue')
    # [2015/17/06-20:10:16][footprints.collectors][pickup:0151][WARNING]: No 'fruit' found in description
        dict(
            couleur = 'bleue',
            fruit = None,
        )

    Report Footprint-Fruit:

        fruits.Ananas
            origine    : {'why': 'Missing value'}

        fruits.Fraise
            couleur    : {'args': 'bleue', 'why': 'Not in values'}

        fruits.Pomme
            couleur    : {'args': 'bleue', 'why': 'Not in values'}

        verger.GrannySmith
            couleur    : {'args': 'bleue', 'why': 'Not in values'}
            calibre    : {'args': 2, 'why': 'Not in values'}

        verger.Zorg
            recolte    : {'only': 'Do not match', 'args': (2001, 2007)}

Et si maintenant nous disons que la récolte par défaut est celle de 2007::

    >>> fp.setup.defaults(recolte=2007)
    >>> fp.proxy.fruit(couleur='bleue')
    <verger.Zorg object at 0x7f4281653e90>

Sélection par intervalles
-------------------------

Pour un paramètre (ou attribut), il est possible d'étendre le filtre *only* avec les modificateurs
*before_* et *after_*.

Nous pouvons avoir ainsi une vision futuriste des pommes Zorg::

    class Zorg(fruits.Pomme):
        _footprint = dict(
            attr = dict(
                couleur = dict(
                    values = ['bleue'],
                ),
            ),
            only = dict(
                after_recolte = 2033,
            )
        )

Et à l'usage::

    >>> fp.setup.defaults(recolte=2051)
    >>> fp.proxy.fruit(couleur='bleue')
    <verger.Zorg object at 0x7f5f3bee1d10>

On pourrait utiliser simultanément les modificateurs *before_* et *after_*, à charge pour le concepteur
de spécifier une intersection non vide si il veut que sa classe soit instanciée un jour.

==========================
Mécanismes de substitution
==========================

Les valeurs servant à la résolution des empreintes de classes n'ont pas besoin d'être
toutes explicites. Il est possible de se référer aux valeurs que prennent certaines de ces valeurs
pour en renseigner d'autres.

.. note:: Merci d'ajouter des exemples et davantage de détails...


=================
Et plus encore...
=================

Multi-collection
----------------

Il ne vous aura pas échappé que la variable de classe **_collector** prenait la forme d'un :func:`tuple`.
Jusque là nous n'avons renseigné cette variable qu'avec une valeur unique. Mais nous pourrions "enregistrer"
une classe auprès de plusieurs collecteurs simultanément, multipliant ainsi les modalités selon lesquelles
cette classe pourrait participer à des résolutions d'empreinte.

Pour ne reprendre que le début de la classe de base des fruits, nous aurions pu écrire::

    class Fruit(fp.FootprintBase):
        _collector = ('fruit', 'nourriture')
        ...

Et nos appétissantes pommes ou fraises, pourraient alors tout aussi bien être obtenues par une demande
de nourriture::

    >>> fp.collectors.keys()
    ['fruit', 'nourriture']
    >>> fp.proxy.nourriture(couleur='jaune')
    <fruits.Pomme object at 0x7fd03dd1f0d0>


Réutilisation d'instances
-------------------------

Instancier des objets n'est pas forcément dispendieux. Mais il est des cas où l'on préférerait réutiliser des objets
déjà venus au monde, dans la mesure où leurs caractéristiques seraient compatibles avec ce que l'on spécifierait
par ailleurs au mécanisme de chargement de base.

Cette fonctionnalité existe: au lieu d'utiliser la méthode :meth:`~footprints.collectors.Collector.load`
du collecteur, on va utiliser la méthode :meth:`~footprints.collectors.Collector.default` qui a exactement
la même interface. Si un objet compatible (au sens de la résolution des footprints) a déjà été créé, il nous
le renvoie, sinon, il est créé.

C'est ce que nous allons faire avec nos pommes, car les pommes c'est bon à deux surtout. Donc autant récupérer
la même. Et pour varier plus encore les plaisirs, nous allons utiliser une autre façon d'effectuer la récupération
de notre fruit préféré::

    >>> p_adam = fp.load(tag='fruit', couleur='jaune')
    >>> p_eve = fp.default(tag='fruit', couleur='jaune')
    >>> p_adam is p_eve
    True

La compatibilité est une notion assez... permissive en fait, car toute valeur non explicitement
rejetée peut faire l'affaire. Et nous aurions aussi bien pu demander pour la seconde pomme::

    >>> p_eve = fp.default(tag='fruit')
    >>> p_adam is p_eve
    True

Si l'on regarde le catalogue de toutes les instances de fruits créées (car le collecteur garde aussi la trace
des objets qu'il a instanciés), il n'y a qu'un seul fruit, la pomme::

    >>> fp.proxy.fruits.instances()
    [<fruits.Pomme object at 0x7f350a22a490>]
    >>> p = fp.proxy.fruits.instances().pop()
    >>> p is p_eve
    True
    >>> p.footprint.info
    'Fruit defendu'

Nous verrons que certaines classes de VORTEX correspondent assez bien à cette modalité d'utilisation (l'interface
système, la cible d'exécution, etc.)

Instanciation directe
---------------------

Nous avons vu que la façon la plus simple d'obtenir un objet le plus adapté à ce que nous savons de ses
caractéristiques (en tout cas celle qui sont accessibles via l'empreinte) est d'invoquer
la commande :meth:`~footprints.collectors.Collector.load`, ou plus élégamment encore, de passer par le proxy
du package.

Mais comme il est interdit d'interdire, il se trouve qu'il reste totalement possible d'instancier directement
une classe, à la dure, pourrait-on dire. Reprenons nos pommes::

    >>> p = fruits.Pomme(couleur='rouge')
    >>> print p.couleur
    rouge
    >>> print p.calibre
    2

Nous disposons tout de même, à titre gracieux en quelque sorte, de tous les mécanismes de résolution
de footprints exposées précédemment: typage, *remap* de valeur, vérification des valeurs autorisées ou exclues, etc.

Explicite ou implicite
----------------------

Le cas extrême de la résolution d'un footprint serait le cas... où il n'y aurait rien à résoudre, par exemple
parce que tous les attributs seraient optionnels et qu'aucune valeur ne serait spécifiée au moment de la résolution.

Par défaut une classe qui hérite de :class:`footprints.FootprintBase` se doit d'avoir au moins *un* attribut
obligatoire. Si ce n'est pas le cas, une exception est levée dès la création de la classe par l'interpréteur
python. C'est une assurance qu'une classe ne parasitera pas les résolutions de footprints.

Mais encore une fois, il n'y a pas de règle absolue en la matière. Et il est possible dans la déclaration d'une
classe de préciser qu'elle n'a pas besoin d'être explicite.

Imaginons, un *Truc* qui soit une *chose* avec un seul argument, optionnel::

    class Truc(fp.FootprintBase):
        _collector = ('chose',)
        _footprint = dict(
            attr = dict(
                bidon = dict(
                    optional = True,
                    default = 'euh...',
                )
            )
        )


Nous obtenons au chargement python:

.. code-block:: python

    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "/home/sevault/git-dev/vortex/site/footprints/__init__.py", line 637, in __new__
        raise FootprintInvalidDefinition('Explicit class without any mandatory footprint attribute.')
    footprints.FootprintInvalidDefinition: Explicit class without any mandatory footprint attribute.

Reprenons alors notre définition, en signifiant que la classe est à résolution implicite::

    class Truc(fp.FootprintBase):
        _explicit  = False
        _collector = ('chose',)
        _footprint = dict(
            attr = dict(
                bidon = dict(
                    optional = True,
                    default = 'euh...',
                )
            )
        )

Plus d'erreur de chargement et nous pouvons instancier une chose aveuglément::

    >>> z = fp.proxy.chose()
    >>> print z
    <__main__.Truc object at 0x7f0c61bb1a10 | footprint=1>
    >>> print z.bidon
    euh...

Pas de doute, la science avance...

Aide en ligne
-------------

Les classes avec résolution d'empreintes sont autodocumentées... pour ce qui relève du footprint qui est
présenté de façon extensive (résultat du merge d'héritage). Pour le reste, pas de mystère, il faut écrire
la doc généraliste...

.. code-block:: python

    >>> help(verger.GrannySmith)

    Help on class GrannySmith in module verger:

    class GrannySmith(fruits.Pomme)
     |  Not documented yet.
     |
     |  Footprint::
     |
     |    dict(
     |        attr = dict(
     |            calibre = dict(
     |                access = 'rxx',
     |                alias = set([]),
     |                default = 2,
     |                optional = True,
     |                outcast = set([]),
     |                remap = dict(),
     |                type = int,
     |                values = set([3, 4, 5, 6, 7]),
     |            ),
     |            couleur = dict(
     |                access = 'rxx',
     |                alias = set([]),
     |                default = None,
     |                optional = False,
     |                outcast = set([]),
     |                remap = dict(
     |                    vert = 'verte',
     |                ),
     |                values = set(['verte', 'vert']),
     |            ),
     |            producteur = dict(
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
     |        info = 'Fruit defendu',
     |        only = dict(),
     |        priority = dict(
     |            level = footprints.priorities.PriorityLevel('DEFAULT'),
     |        ),
     |    )
     |
     |  Method resolution order:
     |      GrannySmith
     |      fruits.Pomme
     |      fruits.Fruit
     |      footprints.FootprintBase
     |      __builtin__.object
     |
     |  Data descriptors defined here:
     |
     |  calibre
     |      Undocumented footprint attribute
     |
     |  couleur
     |      Undocumented footprint attribute
     |
     |  producteur
     |      Undocumented footprint attribute
     |
     |  ----------------------------------------------------------------------
     |  Methods inherited from footprints.FootprintBase:
     |
     | ...

De nombreuses méthodes de classe ou méthodes objets renvoient des informations partielles, sur le footprint,
les valeurs autorisées, etc. Voir la documentation en ligne de la classe :class:`~footprints.FootprintBase`.

Méthodes des collecteurs
------------------------

Mécanismes de filtre, d'élimination d'éléments du collecteur, gestion des instances, etc.

.. note:: documentation à compléter...

======================
Autres fonctionnalités
======================

En interne le package footprint s'appuie sur quelques utilitaires ou implémente
quelques *patterns* qu'il est tout à fait possible d'utiliser en dehors des
classes de type :class:`footprints.FootprintBase`.

Il s'agit notamment du système de loggers, des observers, d'une classe-fabrique
par *tag* : ceux-ci sont hébergés dans le package :mod:`bronx`.

Enfin, un mécanisme d'expansion de modèle descriptif est utilisé (voir ci-dessous).

Mécanismes d'expansion
----------------------

Puisque la résolution d'empreintes de classes se fait sur la base d'une description prenant la forme
d'une liste de clés/valeurs, il est plus que raisonnable d'imaginer que l'on souhaite pouvoir effectuer
quelques mécanismes d'expansion de ladite liste en fonction de certaines des valeurs proposées.

C'est la fonction :func:`footprints.util.expand` qui se charge de ce très utile boulot, en collaboration
éventuelle avec :func:`bronx.stdtypes.date.timeintrangex`.

La première expansion à laquelle on puisse penser est naturellement celle des types de base python itérables
que sont les :func:`list`, :func:`tuple`, :func:`set`, et dans une certaine mesure :func:`dict`
(plus complexe, mais nous verrons ça plus tard).

Mais c'est aussi le cas pour les chaînes de caractères contenant des "range", ou contenant des valeurs
séparées par des virgules, et même contenant des indications de *globbing* !


.. seealso::

   Plus de détails sont données dans la documentaiton de la fonction
   :func:`footprints.util.expand`.

==========
Conclusion
==========

.. seealso::

    La vraie force de la chose est que le choix se fait à des endroits que l'on n'anticipe pas a priori !

=======
Indexes
=======

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
