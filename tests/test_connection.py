##############################################################################
#
# Copyright (c) 2015, 2degrees Limited.
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

from base64 import b64encode
from json import dumps as json_serialize

from nose.tools import assert_equal
from nose.tools import assert_false
from nose.tools import assert_in
from nose.tools import assert_is_instance
from nose.tools import assert_raises
from nose.tools import eq_
from nose.tools import ok_
from requests.adapters import HTTPAdapter as RequestsHTTPAdapter
from requests.models import Response as RequestsResponse

from tests.utils import get_uuid4_str
from twapi_connection import Connection
from twapi_connection.exc import AccessDeniedError
from twapi_connection.exc import AuthenticationError
from twapi_connection.exc import ClientError
from twapi_connection.exc import NotFoundError
from twapi_connection.exc import ServerError
from twapi_connection.exc import UnsupportedResponseError


_STUB_URL_PATH = '/foo'


_STUB_EMAIL_ADDRESS = 'foo@bar.com'

_STUB_PASSWORD = get_uuid4_str()


class TestConnection(object):

    def test_get_request(self):
        self._check_request_sender('GET', 'send_get_request', False)

    def test_head_request(self):
        self._check_request_sender('HEAD', 'send_head_request', False)

    def test_post_request(self):
        self._check_request_sender('POST', 'send_post_request', True)

    def test_post_request_with_no_body(self):
        self._check_request_sender('POST', 'send_post_request', False)

    def test_put_request(self):
        self._check_request_sender('PUT', 'send_put_request', True)

    def test_delete_request(self):
        self._check_request_sender('DELETE', 'send_delete_request', False)

    @staticmethod
    def _check_request_sender(
        http_method_name,
        request_sender_name,
        include_request_body,
        ):
        connection = _MockConnection()

        body_deserialization = {'foo': 'bar'} if include_request_body else None

        request_sender = getattr(connection, request_sender_name)
        request_sender_kwargs = {}
        if include_request_body:
            request_sender_kwargs['body_deserialization'] = body_deserialization
        request_sender(_STUB_URL_PATH, **request_sender_kwargs)

        eq_(1, len(connection.prepared_requests))

        prepared_request = connection.prepared_requests[0]
        eq_(http_method_name, prepared_request.method)

        if include_request_body:
            assert_in('content-type', prepared_request.headers)
            assert_equal(
                'application/json',
                prepared_request.headers['content-type']
            )

        requested_url_path = _get_path_from_api_url(prepared_request.url)
        eq_(_STUB_URL_PATH, requested_url_path)

        if include_request_body:
            body_serialization = json_serialize(body_deserialization)
            eq_(body_serialization, prepared_request.body)
        else:
            assert_false(prepared_request.body)

    def test_absolute_api_url(self):
        connection = _MockConnection()

        api_absolute_url = Connection._API_URL + _STUB_URL_PATH
        connection.send_get_request(api_absolute_url)

        prepared_request = connection.prepared_requests[0]
        eq_(api_absolute_url, prepared_request.url)

    def test_custom_base_api_url(self):
        api_url = 'http://example.com'
        connection = _MockConnection(api_url=api_url)

        connection.send_get_request(_STUB_URL_PATH)

        prepared_request = connection.prepared_requests[0]
        eq_(api_url + _STUB_URL_PATH, prepared_request.url)

    def test_user_agent(self):
        connection = _MockConnection()

        connection.send_get_request(_STUB_URL_PATH)

        prepared_request = connection.prepared_requests[0]
        assert_in('User-Agent', prepared_request.headers)

        user_agent_header_value = prepared_request.headers['User-Agent']
        ok_(user_agent_header_value.startswith('2degrees Python Client/'))

    def test_request_timeout(self):
        connection = _MockConnection(timeout=1)
        connection.send_get_request(_STUB_URL_PATH)
        eq_(1, connection.adapter.timeout)

    def test_json_response(self):
        """
        The output of "200 OK" responses with a JSON body is that body
        deserialized.

        """
        expected_body_deserialization = {'foo': 'bar'}
        response_data_maker = _ResponseMaker(
            200,
            expected_body_deserialization,
            'application/json',
            )
        connection = _MockConnection(response_data_maker)

        response_data = connection.send_get_request(_STUB_URL_PATH)

        eq_(expected_body_deserialization, response_data)

    def test_unexpected_response_status_code(self):
        """
        An exception is raised when the response status code is unsupported.

        """
        unsupported_response_data_maker = _ResponseMaker(304)
        connection = _MockConnection(unsupported_response_data_maker)

        with assert_raises(UnsupportedResponseError) as context_manager:
            connection.send_get_request(_STUB_URL_PATH)

        exception = context_manager.exception
        eq_('Unsupported response status 304', str(exception))

    def test_unexpected_response_content_type(self):
        """
        An exception is raised when the response status code is 200 but the
        content type is not "application/json".

        """
        unsupported_response_data_maker = \
            _ResponseMaker(200, 'Text', 'text/plain')
        connection = _MockConnection(unsupported_response_data_maker)

        with assert_raises(UnsupportedResponseError) as context_manager:
            connection.send_get_request(_STUB_URL_PATH)

        exception = context_manager.exception
        eq_('Unsupported response content type text/plain', str(exception))

    def test_missing_response_content_type(self):
        """An exception is raised when the content type is missing."""
        unsupported_response_data_maker = _ResponseMaker(200, 'Text')
        connection = _MockConnection(unsupported_response_data_maker)

        with assert_raises(UnsupportedResponseError) as context_manager:
            connection.send_get_request(_STUB_URL_PATH)

        exception = context_manager.exception
        eq_('Response does not specify a Content-Type', str(exception))

    def test_response_content_length_is_zero(self):
        response_data_maker = _ResponseMaker(200, None, 'application/json')
        connection = _MockConnection(response_data_maker)

        response_data = connection.send_head_request(_STUB_URL_PATH)

        eq_(None, response_data)

    def test_context_manager(self):
        with _MockConnection() as connection:
            assert_is_instance(connection, _MockConnection)

        assert_false(connection.adapter.is_open)

    def test_keep_alive(self):
        connection = _MockConnection()
        connection.send_get_request(_STUB_URL_PATH)
        ok_(connection.adapter.is_keep_alive_always_used)


class TestErrorResponses(object):

    def test_server_error_response(self):
        response_data_maker = _ResponseMaker(500)
        connection = _MockConnection(response_data_maker)
        with assert_raises(ServerError) as context_manager:
            connection.send_get_request(_STUB_URL_PATH)

        exception = context_manager.exception
        eq_(500, exception.http_status_code)
        eq_('500 Reason', repr(exception))
        eq_('500 Reason', str(exception))

    def test_client_error_response(self):
        response_data_maker = _ResponseMaker(400, {})
        connection = _MockConnection(response_data_maker)

        with assert_raises(ClientError) as context_manager:
            connection.send_get_request(_STUB_URL_PATH)

    def test_resource_not_found_response(self):
        response_data_maker = _ResponseMaker(404, {})
        connection = _MockConnection(response_data_maker)

        with assert_raises(NotFoundError) as context_manager:
            connection.send_get_request(_STUB_URL_PATH)

    def test_forbidden_response(self):
        response_data_maker = _ResponseMaker(403, {})
        connection = _MockConnection(response_data_maker)

        with assert_raises(AccessDeniedError) as context_manager:
            connection.send_get_request(_STUB_URL_PATH)


class TestAuthentication(object):

    def test_valid_credentials(self):
        connection = _MockConnection()
        response_data = connection.send_get_request(_STUB_URL_PATH)
        prepared_request = connection.prepared_requests[0]
        authentication_header_value = prepared_request.headers['authorization']
        expected_header_value = \
            _get_basic_auth(_STUB_EMAIL_ADDRESS, _STUB_PASSWORD)
        eq_(expected_header_value, authentication_header_value)

    def test_invalid_credentials(self):
        incorrect_password = get_uuid4_str()
        connection = _MockConnection(
            email_address=_STUB_EMAIL_ADDRESS,
            password=incorrect_password,
            response_data_maker=_ResponseMaker(401, {}),
            )
        with assert_raises(AuthenticationError):
            connection.send_get_request(_STUB_URL_PATH)

        prepared_request = connection.prepared_requests[0]
        authentication_header_value = prepared_request.headers['authorization']
        expected_header_value = \
            _get_basic_auth(_STUB_EMAIL_ADDRESS, incorrect_password)
        eq_(expected_header_value, authentication_header_value)


class _MockConnection(Connection):

    def __init__(
        self,
        response_data_maker=None,
        email_address=_STUB_EMAIL_ADDRESS,
        password=_STUB_PASSWORD,
        *args,
        **kwargs
        ):
        super_class = super(_MockConnection, self)
        super_class.__init__(email_address, password, *args, **kwargs)

        self.adapter = _MockRequestsAdapter(response_data_maker)
        self._session.mount(self._api_url, self.adapter)

    @property
    def prepared_requests(self):
        return self.adapter.prepared_requests


class _MockRequestsAdapter(RequestsHTTPAdapter):

    def __init__(self, response_data_maker=None, *args, **kwargs):
        super(_MockRequestsAdapter, self).__init__(*args, **kwargs)

        self._response_data_maker = \
            response_data_maker or _ResponseMaker(200, '', 'application/json')

        self.prepared_requests = []
        self.is_keep_alive_always_used = True
        self.is_open = True
        self.timeout = None

    def send(self, request, stream=False, timeout=None, *args, **kwargs):
        is_keep_alive_implied = not stream
        self.is_keep_alive_always_used &= is_keep_alive_implied

        self.timeout = timeout

        self.prepared_requests.append(request)

        response = self._response_data_maker(request)
        return response

    def close(self, *args, **kwargs):
        self.is_open = False

        return super(_MockRequestsAdapter, self).close(*args, **kwargs)


class _ResponseMaker(object):

    def __init__(self, status_code, body_deserialization='', content_type=None):
        super(_ResponseMaker, self).__init__()

        self._status_code = status_code
        self._body_deserialization = body_deserialization
        self._content_type = content_type

    def __call__(self, request):
        response = RequestsResponse()

        response.status_code = self._status_code
        response.reason = 'Reason'

        if self._content_type:
            content_type_header_value = \
                '{}; charset=UTF-8'.format(self._content_type)
            response.headers['Content-Type'] = content_type_header_value

        if self._body_deserialization is None:
            response._content = ''
        else:
            response._content = \
                json_serialize(self._body_deserialization).encode('utf-8')

        return response


def _get_path_from_api_url(api_url):
    assert api_url.startswith(Connection._API_URL)

    api_url_length = len(Connection._API_URL)
    api_url_path_and_query_string = api_url[api_url_length:]
    api_url_path = api_url_path_and_query_string.split('?')[0]
    return api_url_path


def _get_basic_auth(username, password):
    credentials = '%s:%s' % (username, password)
    credentials_encoded = credentials.encode('latin1')
    basic_auth = \
        'Basic ' + b64encode(credentials_encoded).strip().decode('latin1')
    return basic_auth
