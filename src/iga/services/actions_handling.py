# -*- coding: utf-8 -*-

"""
Interface for sending messages, products...
The main class ActionsLoader contains the main methods so as to handle
actions related to sending.
"""

#: No automatic export
__all__ = []

import actions

class ActionsLoader(object):
    """
    Main interface to perform sending actions
    By default, it uses the actions module, but a user can provide its own
    module as long as the correct methods are provided:

      * execute, get_status, on and off.

    Moreover these methods are associated with actions. For now, we provide
    four kinds of action:

      * mail, alarm, sendbdap, routing

    It means that the substitute module must offer the four methods from above
    and accept the four kind of action as argument.
    """

    def __init__(self, def_module=actions):
        self._def_module = def_module

    def dispatch(self, command, action_type=None, **kw):
        if hasattr(self._def_module, command):
            method = getattr(self._def_module, command)
            if action_type:
                return method(action_type)
            else:
                return method(**kw)
        else:
            raise Exception

    def mail(self, **kw):
        """
        Entry point for sending email.
        This function must be used so as to send two kinds of email:

          * a simple text message,
          * an email with an attached file

        Argument:

          * kw (dict): mandatory named arguments to realize the action as sender, recipient...
        """
        #add action_type=mail in the dictionary kw
        #the name of the key is explicitly written
        kw['action_type'] = 'mail'
        self.dispatch('execute', **kw)

    def alarm(self, **kw):
        """
        Entry point for sending alarm.
        This function allows the user to send alarm to the supervision via syslog-ng
        or to log a message.

        Argument:

          * kw (dict): mandatory names arguments to realize the action as the message...
        """
        #add action_type=alarm in the dictionary kw
        #the name of the key is explicitly written
        kw['action_type'] = 'alarm'
        self.dispatch('execute', **kw)

    def sendbdap(self, **kw):
        """
        Entry point for sending product.
        This function allows the user to send product to the BDAP machine.

        Argument:

          * kw (dict): mandatory names arguments to realize the action
                       as the message and the current system so to be able to do
                       the system call.
        """
        #add action_type=sendbdap in the dictionary kw
        #the name of the key is explicitly written
        kw['action_type'] = 'sendbdap'
        self.dispatch('execute', **kw)

    def route(self, **kw):
        """
        Entry point for routing product.
        This function allows the user to send product to the Soprano servers.

        Argument:

          * kw (dict): mandatory names arguments to realize the action
                       as the message and the current system so to be able to do
                       the system call.
        """
        #add action_type=route in the dictionary kw
        #the name of the key is explicitly written
        kw['action_type'] = 'route'
        self.dispatch('execute', **kw)

    def mail_status(self):
        """Return the mail status: True for on and False for off"""
        return self.dispatch('get_status', 'mail')

    def alarm_status(self):
        """Return the alarm status: True for on and False for off"""
        return self.dispatch('get_status', 'alarm')

    def sendbdap_status(self):
        """Return the sendbdap status: True for on and False for off"""
        return self.dispatch('get_status', 'sendbdap')

    def routing_status(self):
        """Return the routing status: True for on and False for off"""
        return self.dispatch('get_status', 'route')

    def mail_on(self):
        """Switch the mail status to on."""
        self.dispatch('on', 'mail')

    def mail_off(self):
        """Switch the mail status to off."""
        self.dispatch('off', 'mail')

    def alarm_on(self):
        """Switch the alarm status to on."""
        self.dispatch('on', 'alarm')

    def alarm_off(self):
        """Switch the alarm status to off."""
        self.dispatch('off', 'alarm')

    def sendbdap_on(self):
        """Switch the sendbdap status to on."""
        self.dispatch('on', 'sendbdap')

    def sendbdap_off(self):
        """Switch the sendbdap status to off."""
        self.dispatch('off', 'sendbdap')

    def routing_on(self):
        """Switch the routing status to on."""
        self.dispatch('on', 'route')

    def routing_off(self):
        """Switch the routing status to off."""
        self.dispatch('off', 'route')
