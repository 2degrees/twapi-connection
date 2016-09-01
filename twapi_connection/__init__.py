##############################################################################
#
# Copyright (c) 2015-2016, 2degrees Limited.
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

from http import HTTPStatus
from json import dumps as json_serialize

from pkg_resources import get_distribution
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from requests.sessions import Session

from twapi_connection.exc import AccessDeniedError
from twapi_connection.exc import AuthenticationError
from twapi_connection.exc import ClientError
from twapi_connection.exc import NotFoundError
from twapi_connection.exc import ServerError
from twapi_connection.exc import UnsupportedResponseError

_DISTRIBUTION_NAME = 'twapi-connection'
_DISTRIBUTION_VERSION = get_distribution(_DISTRIBUTION_NAME).version
_USER_AGENT = '2degrees Python Client/' + _DISTRIBUTION_VERSION


_HTTP_CONNECTION_MAX_RETRIES = 3


class Connection:

    _API_URL = 'https://www.2degreesnetwork.com/api'

    def __init__(self, email_address, password, timeout=None, api_url=None):
        super(Connection, self).__init__()

        self._api_url = api_url or self._API_URL

        self._authentication_handler = HTTPBasicAuth(email_address, password)

        self._session = Session()
        self._session.headers['User-Agent'] = _USER_AGENT

        self._timeout = timeout

        http_adapter = HTTPAdapter(max_retries=_HTTP_CONNECTION_MAX_RETRIES)
        self._session.mount('', http_adapter)

    def send_get_request(self, url, query_string_args=None):
        """
        Send a GET request

        :param str url: The URL or URL path to the endpoint
        :param dict query_string_args: The query string arguments

        :return: Decoded version of the ``JSON`` the remote put in \
                the body of the response.

        """
        return self._send_request('GET', url, query_string_args)

    def send_head_request(self, url, query_string_args=None):
        """
        Send a HEAD request

        :param str url: The URL or URL path to the endpoint
        :param dict query_string_args: The query string arguments

        """
        return self._send_request('HEAD', url, query_string_args)

    def send_post_request(self, url, body_deserialization=None):
        """
        Send a POST request

        :param str url: The URL or URL path to the endpoint
        :param dict body_deserialization: The request's body message \
            deserialized

        :return: Decoded version of the ``JSON`` the remote put in \
                the body of the response.
        """
        return self._send_request(
            'POST',
            url,
            body_deserialization=body_deserialization,
            )

    def send_put_request(self, url, body_deserialization):
        """
        Send a PUT request

        :param str url: The URL or URL path to the endpoint
        :param body_deserialization: The request's body message deserialized

        :return: Decoded version of the ``JSON`` the remote put in \
                the body of the response.
        """
        return self._send_request(
            'PUT',
            url,
            body_deserialization=body_deserialization,
            )

    def send_delete_request(self, url):
        """
        Send a DELETE request

        :param str url: The URL or URL path to the endpoint

        :return: Decoded version of the ``JSON`` the remote put in \
                the body of the response.
        """
        return self._send_request('DELETE', url)

    def _send_request(
        self,
        method,
        url,
        query_string_args=None,
        body_deserialization=None,
        ):
        if url.startswith(self._api_url):
            url = url
        else:
            url = self._api_url + url

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
            timeout=self._timeout,
            )

        self._require_successful_response(response)
        self._require_deserializable_response_body(response)

        return response

    @staticmethod
    def _require_successful_response(response):
        if 400 <= response.status_code < 500:
            if response.status_code == HTTPStatus.UNAUTHORIZED:
                exception_class = AuthenticationError
            elif response.status_code == HTTPStatus.FORBIDDEN:
                exception_class = AccessDeniedError
            elif response.status_code == HTTPStatus.NOT_FOUND:
                exception_class = NotFoundError
            else:
                exception_class = ClientError
            raise exception_class()
        elif 500 <= response.status_code < 600:
            raise ServerError(response.reason, response.status_code)

    @classmethod
    def _require_deserializable_response_body(cls, response):
        if response.status_code in (HTTPStatus.OK, HTTPStatus.NO_CONTENT):
            if response.content:
                cls._require_json_response(response)
        else:
            exception_message = \
                'Unsupported response status {}'.format(response.status_code)
            raise UnsupportedResponseError(exception_message)

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
