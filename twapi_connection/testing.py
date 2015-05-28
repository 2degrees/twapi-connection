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

from pyrecord import Record


APICall = Record.create_type(
    'APICall',
    'url',
    'http_method',
    'query_string_args',
    'request_body_deserialization',
    query_string_args=None,
    request_body_deserialization=None,
    )


SuccessfulAPICall = APICall.extend_type(
    'SuccessfulAPICall',
    'response_body_deserialization',
    )


UnsuccessfulAPICall = APICall.extend_type('UnsuccessfulAPICall', 'exception')


class MockConnection(object):
    """Mock representation of a :class:`~twapi.Connection`"""

    def __init__(self, *api_calls_simulators):
        super(MockConnection, self).__init__()

        self._expected_api_calls = []
        for api_calls_simulator in api_calls_simulators:
            for api_call in api_calls_simulator():
                self._expected_api_calls.append(api_call)

        self._request_count = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            return

        expected_api_call_count = len(self._expected_api_calls)
        pending_api_call_count = expected_api_call_count - self._request_count
        error_message = \
            '{} more requests were expected'.format(pending_api_call_count)
        assert expected_api_call_count == self._request_count, error_message

    def send_get_request(self, url, query_string_args=None):
        return self._call_remote_method(url, 'GET', query_string_args)

    def send_head_request(self, url, query_string_args=None):
        return self._call_remote_method(url, 'HEAD', query_string_args)

    def send_post_request(self, url, body_deserialization=None):
        return self._call_remote_method(
            url,
            'POST',
            request_body_deserialization=body_deserialization,
            )

    def send_put_request(self, url, body_deserialization):
        return self._call_remote_method(
            url,
            'PUT',
            request_body_deserialization=body_deserialization,
            )

    def send_delete_request(self, url):
        return self._call_remote_method(url, 'DELETE')

    def _call_remote_method(
        self,
        url,
        http_method,
        query_string_args=None,
        request_body_deserialization=None,
        ):
        self._require_enough_api_calls(url)

        expected_api_call = self._expected_api_calls[self._request_count]

        _assert_request_matches_api_call(
            expected_api_call,
            url,
            http_method,
            query_string_args,
            request_body_deserialization,
            )

        self._request_count += 1

        if isinstance(expected_api_call, UnsuccessfulAPICall):
            raise expected_api_call.exception

        return expected_api_call.response_body_deserialization

    @property
    def api_calls(self):
        api_calls = self._expected_api_calls[:self._request_count]
        return api_calls

    def _require_enough_api_calls(self, url):
        are_enough_api_calls = \
            self._request_count < len(self._expected_api_calls)
        error_message = 'Not enough API calls for new requests ' \
            '(requested {!r})'.format(url)
        assert are_enough_api_calls, error_message


def _assert_request_matches_api_call(
    api_call,
    url,
    http_method,
    query_string_args,
    request_body_deserialization,
    ):
    urls_match = api_call.url == url
    assert urls_match, 'Expected URL {!r}, got {!r}'.format(api_call.url, url)

    query_string_args_match = api_call.query_string_args == query_string_args
    assert query_string_args_match, \
        'Expected query string arguments {!r}, got {!r}'.format(
            api_call.query_string_args,
            query_string_args,
            )

    http_methods_match = api_call.http_method == http_method
    assert http_methods_match, \
        'Expected HTTP method {!r}, got {!r}'.format(
            api_call.http_method,
            http_method,
            )

    request_body_deserializations_match = \
        api_call.request_body_deserialization == request_body_deserialization
    assert request_body_deserializations_match, \
        'Expected request body deserialization {!r}, got {!r}'.format(
            api_call.request_body_deserialization,
            request_body_deserialization,
            )
