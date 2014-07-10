# -*- coding: utf-8 -*-

"""
Authorizations module.

This modules allow the system to check if the processed actions is authorized or
not. Via the sessions module, glove et environment objects support the
verification.
"""

#: No automatic export
__all__ = []

import re
from collections import namedtuple

from vortex.autolog import logdefault as logger
from vortex import sessions
from vortex.tools.config import GenericConfigParser


class GroupHandler(namedtuple('PermsUsersHandler', ('perms', 'users'))):

    def __new__(cls):
        cfgusers = GenericConfigParser('auth-users-groups.ini')
        cfgperms = GenericConfigParser('auth-perms-actions.ini')
        ConstUsers = namedtuple('ConstUsers', cfgusers.sections())
        ConstPerms = namedtuple('ConstPerms', cfgperms.sections())
        return tuple.__new__(cls, (ConstPerms(**cfgperms.as_dict()), ConstUsers(**cfgusers.as_dict())))


def is_qualified_user(user=None):
    """Check if current or specified user is documented in users-groups definitions."""
    if not user:
        user = sessions.glove().user
    gh = GroupHandler()
    return user in gh.users.users


def is_authorized_user(action='void', user=None):
    """
    Check if the user of the current session is authorized
    to perform the specified action. It also checks if
    the rights had been altered in any ways.
    """
    if not user:
        user = sessions.glove().user
    gh = GroupHandler()
    group = gh.users.users.get(user, 'default')
    level = gh.users.groups.get(group, 'low')
    auth = getattr(gh.perms, level, dict()).get(action, False)

    if auth:
        auth = bool(re.match('(?:ok|on|true|1)', auth, re.IGNORECASE))
    else:
        logger.warning("Action %s not authorized for the current user %s", action, user)

    if auth:
        # Check if the permissions were altered
        genuine_gh = GroupHandler()
        if gh.users.groups.get(group, 'low') != genuine_gh.users.groups.get(group, 'low'):
            logger.error("Permissions were altered !!!")

    return auth
