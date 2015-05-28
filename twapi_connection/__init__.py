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

from http.client import FORBIDDEN as HTTP_STATUS_FORBIDDEN
from http.client import NOT_FOUND as HTTP_STATUS_NOT_FOUND
from http.client import OK as HTTP_STATUS_OK
from http.client import UNAUTHORIZED as HTTP_STATUS_UNAUTHORIZED
from json import dumps as json_serialize
from pkg_resources import get_distribution

from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from requests.sessions import Session
from voluptuous import Schema

from twapi_connection.exc import AccessDeniedError
from twapi_connection.exc import AuthenticationError
from twapi_connection.exc import ClientError
from twapi_connection.exc import NotFoundError
from twapi_connection.exc import ServerError
from twapi_connection.exc import UnsupportedResponseError


_DISTRIBUTION_NAME = 'twapi-connection'
_DISTRIBUTION_VERSION = get_distribution(_DISTRIBUTION_NAME).version
_USER_AGENT = '2degrees Python Client/' + _DISTRIBUTION_VERSION


_ERROR_RESPONSE_SCHEMA = Schema(
    {},
    required=True,
    extra=True,
    )


_HTTP_CONNECTION_MAX_RETRIES = 3


class Connection(object):

    _API_URL = 'https://www.2degreesnetwork.com/api'

    def __init__(self, email_address, password):
        super(Connection, self).__init__()

        self._authentication_handler = HTTPBasicAuth(email_address, password)

        self._session = Session()
        self._session.headers['User-Agent'] = _USER_AGENT

        http_adapter = HTTPAdapter(max_retries=_HTTP_CONNECTION_MAX_RETRIES)
        self._session.mount('', http_adapter)

    def send_get_request(self, url_path, query_string_args=None):
        """
        Send a GET request

        :param str url_path: The URL path to the endpoint
        :param dict query_string_args: The query string arguments

        :return: Decoded version of the ``JSON`` the remote put in \
                the body of the response.

        """
        return self._send_request('GET', url_path, query_string_args)

    def send_head_request(self, url_path, query_string_args=None):
        """
        Send a HEAD request

        :param str url_path: The URL path to the endpoint
        :param dict query_string_args: The query string arguments

        """
        self._send_request('HEAD', url_path, query_string_args)

    def send_post_request(self, url_path, body_deserialization=None):
        """
        Send a POST request

        :param str url_path: The URL path to the endpoint
        :param dict body_deserialization: The request's body message \
            deserialized

        :return: Decoded version of the ``JSON`` the remote put in \
                the body of the response.
        """
        return self._send_request(
            'POST',
            url_path,
            body_deserialization=body_deserialization,
            )

    def send_put_request(self, url_path, body_deserialization):
        """
        Send a PUT request

        :param str url_path: The URL path to the endpoint
        :param body_deserialization: The request's body message deserialized

        :return: Decoded version of the ``JSON`` the remote put in \
                the body of the response.
        """
        return self._send_request(
            'PUT',
            url_path,
            body_deserialization=body_deserialization,
            )

    def send_delete_request(self, url_path):
        """
        Send a DELETE request

        :param str url_path: The URL path to the endpoint

        :return: Decoded version of the ``JSON`` the remote put in \
                the body of the response.
        """
        return self._send_request('DELETE', url_path)

    def _send_request(
        self,
        method,
        url_path,
        query_string_args=None,
        body_deserialization=None,
        ):
        url = self._API_URL + url_path

        query_string_args = query_string_args or {}

        request_headers = \
            {'content-type': 'application/json'} if body_deserialization else {}

        if body_deserialization:
            request_body_serialization = json_serialize(body_deserialization)
        else:
            request_body_serialization = None

        response = self._session.request(
            method,
            url,
            params=query_string_args,
            auth=self._authentication_handler,
            data=request_body_serialization,
            headers=request_headers,
            )

        response_body_deserialization = \
            self._deserialize_response_body(response)
        return response_body_deserialization

    @classmethod
    def _deserialize_response_body(cls, response):
        cls._require_successful_response(response)

        if response.status_code == HTTP_STATUS_OK:
            cls._require_json_response(response)
            response_body_deserialization = response.json() or None
        else:
            exception_message = \
                'Unsupported response status {}'.format(response.status_code)
            raise UnsupportedResponseError(exception_message)

        return response_body_deserialization

    @staticmethod
    def _require_successful_response(response):
        if 400 <= response.status_code < 500:
            response_data = response.json()
            error_data = _ERROR_RESPONSE_SCHEMA(response_data)

            if response.status_code == HTTP_STATUS_UNAUTHORIZED:
                exception_class = AuthenticationError
            elif response.status_code == HTTP_STATUS_FORBIDDEN:
                exception_class = AccessDeniedError
            elif response.status_code == HTTP_STATUS_NOT_FOUND:
                exception_class = NotFoundError
            else:
                exception_class = ClientError
            raise exception_class()
        elif 500 <= response.status_code < 600:
            raise ServerError(response.reason, response.status_code)

    @staticmethod
    def _require_json_response(response):
        content_type_header_value = response.headers.get('Content-Type')
        if not content_type_header_value:
            exception_message = 'Response does not specify a Content-Type'
            raise UnsupportedResponseError(exception_message)

        content_type = content_type_header_value.split(';')[0].lower()
        if content_type != 'application/json':
            exception_message = \
                'Unsupported response content type {}'.format(content_type)
            raise UnsupportedResponseError(exception_message)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._session.close()
