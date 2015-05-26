##############################################################################
#
# Copyright (c) 2015, 2degrees Limited.
# All Rights Reserved.
#
# This file is part of twod-api-client
# <https://github.com/2degrees/twod-api-client>, which is subject to the
# provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################


class TwodAPIException(Exception):
    pass


class UnsupportedResponseError(TwodAPIException):
    pass


class ClientError(TwodAPIException):
    pass


class AuthenticationError(ClientError):
    pass


class ServerError(TwodAPIException):
    """
    Remote failed to process the request due to a problem at their end. This
    represents an HTTP response code of 50X.

    :param int http_status_code:

    """
    def __init__(self, message, http_status_code):
        super(ServerError, self).__init__()

        self.message = message
        self.http_status_code = http_status_code

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return '{} {}'.format(self.http_status_code, self.message)
