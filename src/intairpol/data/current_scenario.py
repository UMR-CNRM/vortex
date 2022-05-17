# -*- coding: utf-8 -*-

"""
Current scenario to keep track of running scenario in operation
(where xpid is constant).

Successive tasks need to retrieve this current scenario to fetch
ressource created earlier (with the same scenario)
"""

from __future__ import print_function, absolute_import, unicode_literals, division


from vortex.data.contents import JsonDictContent
from vortex.data.outflow import ModelResource


class CurrentScenarioContent(JsonDictContent):
    """
    Content of CurrentScenario.
    """

    @property
    def scenario(self):
        """Scenario."""
        return self._data["scenario"]

    @property
    def state(self):
        """State of current scenario (running, done, failed, ...)."""
        return self._data["state"]

    @property
    def started_at(self):
        """When did the scenario start ?"""
        return self._data["started_at"]

    def is_running(self):
        """Is the scenario already running."""
        return self.state == "running"

    def is_done(self):
        """Is the scenario finished ?"""
        return self.state == "done"

    def has_failed(self):
        """Has the scenario failed ?"""
        return self.state == "failed"

    def mark_running(self):
        """Mark the scenario as running."""
        self._data["state"] = "running"

    def mark_done(self):
        """Mark the scenario as finished."""
        self._data["state"] = "done"

    def mark_failed(self):
        """Mark the scenario as failed."""
        self._data["state"] = "failed"


class CurrentScenario(ModelResource):
    """Used to retrieve current scenario."""

    # fmt: off
    _footprint = [
        dict(
            info = "Store current scenario informations",
            attr = dict(
                clscontents = dict(
                    default = CurrentScenarioContent
                ),
                model = dict(
                    values   = ['mocage', ]
                ),
                kind = dict(
                    values = ["current_scenario"]
                ),
                nativefmt = dict(
                    values = ["json"],
                    default = "json"
                ),
            ),
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "current_scenario"
