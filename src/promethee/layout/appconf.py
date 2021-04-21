ll__ = []

import json
import six
import vortex  # noqa: F401
from vortex.layout.nodes import ConfigSet

import promethee  # noqa: F401

import footprints

logger = footprints.loggers.getLogger(__name__)

def recursive_format(element, **format_kwargs):
#    if isinstance(element, (str, unicode)):
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
    def __init__(self, conf, ticket):
        super(ConfigSetPromethee, self).__init__()
        for key, value in conf.items():
            try:
                self[key] = value.strftime("%Y%m%dT%H%M%S")
            except:
                try:
                    self[key] = int(value)
                except:
                    try:
                        self[key] = float(value)
                    except:
                        self[key] = value
        self.ticket = ticket
        self.rootapp_dir = "."
        self.jsonconf = None
        try:
            self.rootapp_dir = self.path.dirname(self.path.dirname(self.iniconf))
            self.jsonconf = self.iniconf.rstrip("ini") + "json"
        except:
            logger.warning("Missing mandatory attribute 'iniconf'.")

        if self.path.isfile(self.jsonconf):
            try:
                with open(self.jsonconf) as jsonf:
                    self.update(**json.load(jsonf))
            except:
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
        new_update_kwargs = recursive_format(update_kwargs, **self)
        super(ConfigSetPromethee, self).update(**new_update_kwargs)
        self.format(**update_kwargs)

    def format(self, **format_kwargs):
        for key, value in self.items():
            self[key] = recursive_format(value, **format_kwargs)

    def get_step_conf(self, step):
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

