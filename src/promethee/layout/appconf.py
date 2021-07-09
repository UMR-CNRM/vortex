#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Promethee Application Configuration features.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import io
import json
import six
import vortex  # noqa: F401
from vortex.layout.nodes import ConfigSet

import promethee  # noqa: F401

import footprints

logger = footprints.loggers.getLogger(__name__)

__all__ = []

def recursive_format(element, **format_kwargs):
    """
    Function which applies string formatting to a given element (if of type
    str or unicode) or recursively applies the string to the sub-elements of
    the given element (if of type dict or list).

    A few examples:

    >>> recursive_format("{son}, I am your father.", son="luke")
    'luke, I am your father'
    >>> recursive_format(u'{daughter} and {son}, I am your father', daughter="leia", son="luke")
    u'leia and luke, I am your father'
    >>> my_kwargs = {"father" : "anakin", "mother": "padme", "son":"luke", "daughter":"leia", "age":42}
    >>> recursive_format({"A" : "My name is {father}", "B" : "I'm Vader", "C": "My kids are {kids}"}, **my_kwargs)
    {"A" : "My name is anakin", "B" : "I used to be fun", "C": "My kids are {kids}"}
    >>> recursive_format({"A":[{"B":{"deeply":"At {age}, I still love {mother}"}}]}, **my_kwargs)
    {"A":[{"B":{"deeply":"At 42, I still love padme"}}]}

    Arguments description:

    * element (any): Element to string-format or dict/list of elements to string-format

    It returns:

    * type(element): Formatted given element

    """
    if isinstance(element, six.string_types):
        try:
            return element.format(**format_kwargs)
        except KeyError:
            return element
    if isinstance(element, list):
        return [recursive_format(value, **format_kwargs) for value in element]
    if isinstance(element, dict):
        for key, value in element.items():
            element[key] = recursive_format(value, **format_kwargs)
        return element
    return element


class ConfigSetPromethee(ConfigSet):
    """Custom Promethee application configuration set.

    It is an extension of the usual vortex.layout.nodes.ConfigSet of a task, composed
    by some environment variables and the constants declared in the .ini
    configuration file. The ConfigSetPromethee will search for another configuration
    file following the <vapp>_<conf>.json naming standard (like the usual ini file)
    and add the elements retrieved to the given config set.

    This new json configuration file gathers all the footprints of the resources,
    providers and algo components used in the application. It has been conceived
    to factorize the task writing, and to serialize the resource fetch/backup.
    This configuration file has the following structure:

    >>> {
    ...     'providers' : {
    ...         'provider_1': {...},
    ...         'provider_2': {...}
    ...     },
    ...     'resources' : {
    ...         'resource_1': {...},
    ...         'resource_2': {...}
    ...     },
    ...     'algos' : {
    ...         'algo_component_1': {...}
    ...     },
    ...     'tasks' : {
    ...         'task_1' : {
    ...             'all' : {},
    ...             'early-fetch' : {},
    ...             'fetch' : {
    ...                 'resource_1': 'provider_1'
    ...             },
    ...             'compute' : 'algo_component_1',
    ...             'backup' : {
    ...                 'resource_2': ['provider_1', 'provider_2']
    ...             },
    ...             'late-backup' : {}
    ...         }
    ...     }
    ... }

    The ConfigSetPromethee thus assembles the task layout, and full ressources
    handlers can be accessed like a dictionnary through the 'get_step_conf'
    method. For instance:

    >>> conf = ConfigSetPromethee(self.conf, self.ticket)
    >>> toolbox.input(**conf.get_step_conf("fetch")["resource_1"])
    ... # {...} (input resource handler combining the 'resource_1' and 'provider_1' as configured later)
    >>> [toolbox.output(**rh) for rh in toolbox.output("backup").values()]
    ... # {...} (output resource handler combining the 'resource_2' and 'provider_1')
    ... # {...} (output resource handler combining the 'resource_2' and 'provider_2')

    Inheritance:

    * :class:`vortex.layout.nodes.ConfigSet`

    Arguments description:

    * conf (:class:`vortex.layout.nodes.ConfigSet`, or dict-like): Classical application
      configuration set resulting from the env and .ini configuration file parsing.
    * ticket (`class:`vortex.sessions.Ticket`): Session's ticket.

    """
    def __init__(self, conf, ticket):
        super(ConfigSetPromethee, self).__init__()
        for key, value in conf.items():
            try:
                self[key] = value.strftime("%Y%m%dT%H%M%S")
            except Exception:
                try:
                    self[key] = int(value)
                except Exception:
                    try:
                        self[key] = float(value)
                    except Exception:
                        self[key] = value
        self.ticket = ticket
        self.rootapp_dir = "."
        self.jsonconf = None
        try:
            self.rootapp_dir = self.path.dirname(self.path.dirname(self.iniconf))
            self.jsonconf = self.iniconf.rstrip("ini") + "json"
        except Exception:
            logger.warning("Missing mandatory attribute 'iniconf'.")

        if self.path.isfile(self.jsonconf):
            try:
                with io.open(self.jsonconf, 'r', encoding='utf-8') as jsonf:
                    self.update(**json.load(jsonf))
            except Exception:
                logger.error("Failed to retrieve json config", exc_info=True)
        self.steps = dict()
        if "tasks" in self and "task" in self:
            self.steps = self.pop("tasks")[self["task"]]
        self.format(**self)

    @property
    def path(self):
        return self.ticket.sh.path

    def has_jsonconf(self):
        return self.path.isfile(self.jsonconf)

    def update(self, **update_kwargs):
        """
        Update the 'self' config set by adding the 'update_kwargs' to the
        'self' config set and by recursively formatting its elements according to
        the given 'update_kwargs'.
        """
        new_update_kwargs = recursive_format(update_kwargs, **self)
        super(ConfigSetPromethee, self).update(**new_update_kwargs)
        self.format(**update_kwargs)

    def format(self, **format_kwargs):
        """
        Format recursively the elements of the 'self' config set
        according to the given 'format_kwargs'.
        """
        for key, value in self.items():
            self[key] = recursive_format(value, **format_kwargs)

    def get_step_conf(self, step):
        """
        Builds the step configuration of an application task and returns all
        the resource handlers configs to use in the step.

        To do so, it finds all the resources and providers used in the given step
        and combines their configured footprints. The resource handlers configs are
        then accessible like in a dictionnary.

        It is important to differentiate the types of steps:

        * "all", "early-fetch" and "fetch" are input steps. It means that all the
          given resources are to be processed with a toolbox.input().get()
        * "compute" is a computational step. The given footprint is an algo component
          footprint, and thus is to be run like so.
        * "backup" and "late-backup" are output steps. It means that all the given
          resources are to be processed with a toolbox.output().put(). Also we
          can associate several providers to a single resource in the case we would
          like to feed several providers of a single resource.

        Arguments description:

        * step (str): step name

        It returns:

        * dict: Step configuration

        """
        step_conf = dict()
        if step in ["all", "early-fetch", "fetch"]:
            for resource, provider in self.steps[step].items():
                step_conf[resource] = dict()
                step_conf[resource].update(self["resources"][resource])
                step_conf[resource].update(self["providers"][provider])

        elif step == "compute":
            step_conf = self["algos"][self.steps["compute"]]

        elif step in ["backup", "late-backup"]:
            for resource, providers in self.steps[step].items():
                for provider in providers:
                    res_prov = resource + "_" + provider
                    step_conf[res_prov] = dict()
                    step_conf[res_prov].update(self["resources"][resource])
                    step_conf[res_prov].update(self["providers"][provider])
        return step_conf
