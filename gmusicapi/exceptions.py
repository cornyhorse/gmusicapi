# -*- coding: utf-8 -*-

"""Custom exceptions used across the project."""
from __future__ import print_function, division, absolute_import, unicode_literals


class CallFailure(Exception):
    """Exception raised when a Google Music server responds that a call failed.

    Attributes:
        callname -- name of the protocol.Call that failed
    """
    def __init__(self, message, callname):
        Exception.__init__(self, message)

        self.callname = callname

    def __str__(self):
        return "%s: %s" % (self.callname, Exception.__str__(self))


class ParseException(Exception):
    """Thrown by Call.parse_response on errors."""
    pass


class ValidationException(Exception):
    """Thrown by Transaction.verify_res_schema on errors."""
    pass


class AlreadyLoggedIn(Exception):
    pass


class NotLoggedIn(Exception):
    pass


class NotSubscribed(Exception):
    def __init__(self, *args):
        if len(args) >= 1:
            args = list(args)
            args[0] += " (https://goo.gl/v1wVHT)"
            args = tuple(args)
        else:
            args = ("Subscription required. (https://goo.gl/v1wVHT)",)

        self.args = args


class GmusicapiWarning(UserWarning):
    pass


class InvalidDeviceId(Exception):
    def __init__(self, message, ids):
        if ids:
            message += 'Your valid device IDs are:\n* %s' % '\n* '.join(ids)
        else:
            message += 'It looks like your account does not have any '
            'valid device IDs.'
        super(InvalidDeviceId, self).__init__(message)
        self.valid_device_ids = ids
