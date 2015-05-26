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

from urllib.parse import parse_qsl
from urllib.parse import urlsplit

from pyrecord import Record
from voluptuous import Any
from voluptuous import Schema


BATCH_RETRIEVAL_SIZE_LIMIT = 200


User = Record.create_type(
    'User',
    'id',
    'full_name',
    'email_address',
    'organization_name',
    'job_title',
    )


Group = Record.create_type('Group', 'id')


_USER_DATA_SCHEMA = Schema(
    {
        'id': int,
        'full_name': str,
        'email_address': str,
        'organization_name': str,
        'job_title': str
        },
    required=True,
    extra=False,
    )


_DELETED_USER_ID_DATA_SCHEMA = Schema(int)


_GROUP_DATA_SCHEMA = Schema({'id': int}, required=True, extra=False)


_PAGINATED_RESPONSE_SCHEMA = Schema(
    {
        'count': int,
        'next': Any(str, None),
        'results': [],
        },
    required=True,
    extra=True,
    )


def get_users(connection):
    """
    Return information about each user that the client is allowed to know
    about.

    """
    users_data = _get_paginated_data(connection, '/users/')
    for user_data in users_data:
        user_data = _USER_DATA_SCHEMA(user_data)
        user = User(**user_data)
        yield user


def get_deleted_users(connection):
    """Return the identifiers of the users that have been deleted."""
    users_data = _get_paginated_data(connection, '/users/deleted/')
    for user_data in users_data:
        user_ids = _DELETED_USER_ID_DATA_SCHEMA(user_data)
        yield user_ids


def get_groups(connection):
    """
    Return information about each group that the client is allowed to know
    about.

    """
    groups_data = _get_paginated_data(connection, '/groups/')
    for group_data in groups_data:
        group_data = _GROUP_DATA_SCHEMA(group_data)
        group = Group(**group_data)
        yield group


def _get_paginated_data(connection, path_info, query_string_args=None):
    data_by_page = _get_data_by_page(path_info, query_string_args, connection)
    for page_data in data_by_page:
        for datum in page_data:
            yield datum


def _get_data_by_page(path_info, query_string_args, connection):
    has_more_pages = True
    while has_more_pages:
        response = connection.send_get_request(path_info, query_string_args)
        response = _PAGINATED_RESPONSE_SCHEMA(response)

        response_data = response['results']
        yield response_data

        next_page_url = response['next']
        query_string_args = _parse_url_query(next_page_url)
        has_more_pages = bool(next_page_url)


def _parse_url_query(url):
    url_parts = urlsplit(url)
    url_query_raw = url_parts.query
    url_query = dict(parse_qsl(url_query_raw))
    return url_query
