"""
This module defines common base classes for miscellaneous purposes.
"""

import json

from bronx.fancies import loggers

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class ShellEncoder(json.JSONEncoder):
    """Encoder for :mod:`json` dumps method."""

    def default(self, obj):
        """Overwrite the default encoding if the current object has a ``export_dict`` method."""
        if hasattr(obj, "export_dict"):
            return obj.export_dict()
        elif hasattr(obj, "footprint_export"):
            return obj.footprint_export()
        elif hasattr(obj, "__dict__"):
            return vars(obj)
        return super().default(obj)
