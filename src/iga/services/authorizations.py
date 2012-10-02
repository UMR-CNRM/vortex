#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
Authorizations module.

This modules allow the system to check if the processed actions is authorized or
not. Via the sessions module, glove et environment objects support the
verification.
"""

import sys
import logging
from vortex import sessions
from authorizations_handling import GroupHandler, Group, Permissions

#get the current ticket
tck = sessions.current()
#get the attached environment
env = tck.env

class Const(object):
    """
    Const class so as to create const attribute
    """
    def __setattr__(self, name, kw):
        if hasattr(self, 'once'):
            raise AttributeError, 'This attribute should not be overwritten'
        else:
            self.__dict__[name] = kw

class GroupActionsConst(Const):
    """docstring for GroupActionsConst"""
    def __init__(self):
        self._map_group_actions = {
                'root': {
                    'alarm':True,
                    'mail':True,
                    'sendbdap':False,
                    'routing':False
                },
                'low': {
                    'alarm':False,
                    'mail':True,
                    'sendbdap':False,
                    'routing':False
                }
            }
        self._map_users_group = {
                'root' : ['mxpt001', 'root', 'adm', 'oper' ],
                'low' : ['research', 'tourist']
            }
        self.once = True

    def get_const(self, value):
        if value == 1:
            return self._map_group_actions
        elif value == 2:
            return self._map_users_group
        else:
            return None

def prepare_grp():
    """docstring for prepare_grp"""
    group_hdl = GroupHandler()
    gac = GroupActionsConst()
    MAP_GROUP_ACTIONS = gac.get_const(1)
    for grp_name in MAP_GROUP_ACTIONS:
        curr_grp = Group(grp_name)
        curr_perm = Permissions(**MAP_GROUP_ACTIONS[grp_name])
        curr_grp.add_permissions(curr_perm)
        group_hdl.add(curr_grp)
    current_module = sys.modules.get(__name__)
    current_module.group_hdl = group_hdl

def getuser():
    r"""
    Return the “login name” of the user.

    This function checks the environment variables LOGNAME, USER, LNAME and
    USERNAME, in order, and returns the value of the first one which is
    set to a non-empty string. If none are set, the login name from the 
    password database is returned on systems which support the pwd module,
    otherwise, an exception is raised (for now it returns None).
    """
    global env
    _ALIAS = ['LOGNAME', 'USER', 'LNAME', 'USERNAME']
    for elmt in _ALIAS:
        user = env.getvar(elmt)
        if user:
            return user
    return None

prepare_grp()

def is_user_authorized(action_type):
    r"""
    Check different global variables so as to know if the current user is
    allowed to perform the task.

    :returns True or False
    """
    user = getuser()
    grp = None
    b_right = None
    gac = GroupActionsConst()
    MAP_USERS_GROUP = gac.get_const(2)
    for grp_name in MAP_USERS_GROUP:
        if user in MAP_USERS_GROUP[grp_name]:
            grp = grp_name
    if grp:
        #group_hdl became an attribute of the module thanks to prepare function
        #call above
        current_grp = group_hdl.get(grp)
        b_right = current_grp.permissions.get_permission(action_type)
    else:
        logging.error("No group found")
    if not b_right:
        logging.warning("Action %s is not authorized for the current user %s",
                        action_type, user)
    return b_right


