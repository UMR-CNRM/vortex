"""
Factory for named roles.
"""

#: No automatic export
__all__ = []

_activetag = "default"


def stdfactoryrole(role):
    """Standard processing for role names."""
    return "".join([s[0].upper() + s[1:] for s in role.split()])


def switchfactory(tag="default"):
    """Switch the current active factory to the existing one identified through its ``tag``."""
    if tag in _rolesgateway:
        global _activetag
        _activetag = tag


def setfactoryrole(factory=None, tag=None):
    """
    Defines the specified ``factory`` function as the current processing role translator
    associated with ``tag``.
    """
    global _activetag
    if not tag:
        tag = _activetag
    if factory and tag:
        _rolesgateway[tag] = factory


def setrole(role, tag=None):
    """
    Entry point for handling strings ``role``.
    Returns the processed string according to the current active factory name
    or using the one associated with ``tag``.
    """
    if not role:
        return None
    global _activetag
    if not tag:
        tag = _activetag
    return _rolesgateway[tag](role)


_rolesgateway = dict(default=stdfactoryrole)
