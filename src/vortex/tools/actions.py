#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
Module managing the sending of messages. It's the by default module given to the
actions_handling main module.
This module must provide four high level functions:
    -on, off, status, execute.
The on, off and status functions must return a boolean value reflecting the
status of action passed argument. As far as the execute function is concerned,
it must deals with the data (given to realize the action) and the action
to be processed: mail, sendbdap, routing, alarm.  
For now, it also contains several global variables (_ACTIONS_DICT, _MAP_ACTIONS, 
_COMPONENTS). 
_ACTIONS_DICT : determine and store the status of the actions
_MAP_ACTIONS : link an action to a class dedicated to that action
_COMPONENTS : link an action to a service dedicated to that action
"""


import logging

from vortex.utilities.authorizations import is_user_authorized
import services
   
class SendData(object):
    r"""
    This is an abstract class which represent the general way to deal with
    sendind all kind of messages. The method used is:
        - parse the arguments,
        - check if the service is available,
        - check if the user is authorized to realize the action
        - send the message

    Argument: 
        data (dict): named argument, all mandatory parameters for the chosen action
    """
    def __init__(self, action, service):
        self.action = action 
        print "init service", service
        self.service = service

    def available_services(self):
        r"""
        Check if the service is implemented. If that's the case, the attribute
        _currentaction is set to the action to be performed.

        :returns True or False
        """
        #check if the service is available
        if hasattr(getattr(self, self.action), "__func__"):
            self._currentaction = getattr(self, self.action)
            return True
        else:
            logging.warning('Services non available %s', self.action)
            return False

    def send(self):
        r"""
        Call the chosen action pointed by _currentaction.
        """
        #check if the user is authorized to realize the action
        #check if the action can be processed by the instance
        #check if the action is authorized 
        print self.service
        if is_user_authorized(self.service.get_action_type()):
            #patch: so as to work status must be defined in the derived
            #class
            if self.available_services() and self.status():
                self._currentaction()
            else:
                logging.warning('Non authorized action %s', self.action)
        else:
            logging.warning('user not authorized to use %s',
                            self.service.get_action_type())

    def get_service(self):
        return self.service

_RUN_COMMAND = 'execute'
_COMMAND_NAMES = ['_status', '_on', '_off']

def actioninterface(xmodule, _ACTIONS_DICT, _MAP_ACTIONS):
    def on(action):
        """Set the boolean value associated with the passed argument action to True."""
        _ACTIONS_DICT[action] = True
        
    def off(action):
        """Set the boolean value associated with the passed argument action to False."""
        _ACTIONS_DICT[action] = False
    
    def status(action):
        """Return the boolean value associated with the passed argument action."""
        logging.info("Status of %s is %s", action, _ACTIONS_DICT[action])
        return _ACTIONS_DICT[action]
     
    def get_act_serv(**kw):
        """
        Build the instance determined by the action, through
        _MAP_ACTIONS dictionary, and associated with the correct service.
        """
        action_type = kw['action_type']
        ctlg = services.catalog()
        logging.debug("catalogue des services %s", ctlg())
        serv = ctlg.findbest(kw)
        return _MAP_ACTIONS[action_type](action_type, serv)
    
    def execute(**kw):
        """
        Call the send method of the built instance returned by get_act_serv by the action.
        """
        obj = get_act_serv(**kw)
        obj.send()

    xmodule.execute = execute
    xmodule.on = on
    xmodule.off = off
    xmodule.status = status
    xmodule.get_act_serv = get_act_serv

