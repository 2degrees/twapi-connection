##############################################################################
#
# Copyright (c) 2016, 2degrees Limited.
# All Rights Reserved.
#
# This file is part of twapi-connection
# <https://github.com/2degrees/twapi-connection>, which is subject to the
# provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

from nose.tools import assert_in, eq_

from tests.test_connection import MockRequest
from twapi_connection.auth import BearerTokenAuth


def test_bearer_token_auth():
    request = MockRequest()
    token = 'my token'
    authentication_handler = BearerTokenAuth(token)
    request_with_authentication = authentication_handler(request)
    assert_in('Authorization', request_with_authentication.headers)
    eq_('Bearer ' + token, request_with_authentication.headers['Authorization'])
