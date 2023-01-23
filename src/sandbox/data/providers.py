"""
This module contains "fake" provider for demonstration purposes.

Such providers will be triggered based on the experiment name (or location
for uget).
"""

from vortex.data.providers import Vortex
from vortex.syntax.stdattrs import legacy_xpid, demosuites

from gco.data.providers import AbstractUEnvProvider, AbstractUGetProvider
from gco.syntax.stdattrs import AbstractUgetId


class VortexDemo(Vortex):
    """Vortex Demo provider."""

    _footprint = [
        legacy_xpid,
        dict(
            info = 'Vortex provider for demo experiments',
            attr = dict(
                experiment = dict(
                    values = demosuites,
                ),
            ),
        ),
    ]

    def netloc(self, resource):
        """Vortex Demo netloc."""
        return 'vortex-demo.' + self.namespace.domain


class UgetIdDemo(AbstractUgetId):
    """Uget demo IDs."""

    _ALLOWED_LOCATIONS = ('demo', )


class UGetDemoProvider(AbstractUGetProvider):
    """Demo Uget provider."""

    _footprint = dict(
        info = 'Uget Demo provider',
        attr = dict(
            uget = dict(
                type = UgetIdDemo,
            ),
        ),
    )

    def netloc(self, resource):
        """Tweak the desired netloc."""
        ns = super().netloc(resource).split('.')
        ns[0] += '-demo'
        return '.'.join(ns)


class UEnvDemoProvider(AbstractUEnvProvider):
    """Demo Uenv provider."""

    _footprint = dict(
        info = 'UEnv Demo provider',
        attr = dict(
            uenv = dict(
                type = UgetIdDemo,
            ),
        ),
    )

    @property
    def _uenv_netloc(self):
        """Tweak the desired netloc that is used to fetch the Env file."""
        ns = super()._uenv_netloc.split('.')
        ns[0] += '-demo'
        return '.'.join(ns)

    def netloc(self, resource):
        """Tweak the desired netloc."""
        ns = super().netloc(resource).split('.')
        ns[0] += '-demo'
        return '.'.join(ns)
