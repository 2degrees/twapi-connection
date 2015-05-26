from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty
from inspect import isgenerator
from itertools import islice

from nose.tools.trivial import eq_

from twapi import BATCH_RETRIEVAL_SIZE_LIMIT
from twapi import User
from twapi import get_users
from twapi.testing import MockConnection
from twapi.testing import SuccessfulAPICall


class TestUsersRetrieval(object):

    def test_no_users(self):
        simulator = GetUsers([])
        connection = MockConnection(simulator)
        with connection:
            users = list(get_users(connection))
        eq_([], users)

    def test_not_exceeding_pagination_size(self):
        users = self._make_users(BATCH_RETRIEVAL_SIZE_LIMIT - 1)
        simulator = GetUsers(users)
        connection = MockConnection(simulator)
        with connection:
            retrieved_users = list(get_users(connection))
        eq_(users, retrieved_users)

    def test_exceeding_pagination_size(self):
        users = self._make_users(BATCH_RETRIEVAL_SIZE_LIMIT + 1)
        simulator = GetUsers(users)
        connection = MockConnection(simulator)
        with connection:
            retrieved_users = list(get_users(connection))
        eq_(users, retrieved_users)

    @staticmethod
    def _make_users(user_count):
        users = []
        for counter in range(user_count):
            user = User(
                id=counter,
                full_name='User {}'.format(counter),
                email_address='user-{}@example.com'.format(counter),
                organization_name='Example Ltd',
                job_title='Employee {}'.format(counter),
                )
            users.append(user)
        return users


class _PaginatedObjectsRetriever(object):

    __metaclass__ = ABCMeta

    _API_CALL_PATH_INFO = abstractproperty()

    def __init__(self, objects):
        super(_PaginatedObjectsRetriever, self).__init__()
        self._objects_by_page = _paginate(objects, BATCH_RETRIEVAL_SIZE_LIMIT)
        self._objects_count = len(objects)

    def __call__(self):
        api_calls = []

        if self._objects_by_page:
            first_page_objects = self._objects_by_page[0]
        else:
            first_page_objects = []

        first_page_api_call = self._get_api_call_for_page(first_page_objects)
        api_calls.append(first_page_api_call)

        subsequent_pages_objects = self._objects_by_page[1:]
        for page_objects in subsequent_pages_objects:
            api_call = self._get_api_call_for_page(page_objects)
            api_calls.append(api_call)

        return api_calls

    def _get_api_call_for_page(self, page_objects):
        query_string_args = self._get_query_string_args(page_objects)
        response_body_deserialization = \
            self._get_response_body_deserialization(page_objects)
        api_call = SuccessfulAPICall(
            self._API_CALL_PATH_INFO,
            'GET',
            query_string_args,
            response_body_deserialization=response_body_deserialization,
            )
        return api_call

    def _get_query_string_args(self, page_objects):
        page_number = self._get_current_objects_page_number(page_objects)
        if 1 < page_number:
            query_string_args = {'page': str(page_number)}
        else:
            query_string_args = None

        return query_string_args

    def _get_response_body_deserialization(self, page_objects):
        page_number = self._get_current_objects_page_number(page_objects)
        pages_count = len(self._objects_by_page)
        page_has_successors = page_number < pages_count
        if page_has_successors:
            next_page_url = \
                '{}?page={}'.format(self._API_CALL_PATH_INFO, page_number + 1)
        else:
            next_page_url = None

        page_objects_data = self._get_objects_data(page_objects)
        response_body_deserialization = {
            'count': self._objects_count,
            'next': next_page_url,
            'results': page_objects_data,
            }
        return response_body_deserialization

    def _get_current_objects_page_number(self, page_objects):
        if self._objects_by_page:
            page_number = self._objects_by_page.index(page_objects) + 1
        else:
            page_number = 1
        return page_number

    @abstractmethod
    def _get_objects_data(self, objects):
        pass  # pragma: no cover


def _paginate(iterable, page_size):
    return list(_ipaginate(iterable, page_size))


def _ipaginate(iterable, page_size):
    if not isgenerator(iterable):
        iterable = iter(iterable)

    next_page_iterable = _get_next_page_iterable_as_list(iterable, page_size)
    while next_page_iterable:
        yield next_page_iterable

        next_page_iterable = \
            _get_next_page_iterable_as_list(iterable, page_size)


def _get_next_page_iterable_as_list(iterable, page_size):
    next_page_iterable = list(islice(iterable, page_size))
    return next_page_iterable


class GetUsers(_PaginatedObjectsRetriever):
    """Simulator for a successful call to :func:`~twapi.get_users`."""

    _API_CALL_PATH_INFO = '/users/'

    def _get_response_body_deserialization(self, page_objects):
        response_body_deserialization = super(GetUsers, self) \
            ._get_response_body_deserialization(page_objects)

        future_updates_url = ''
        response_body_deserialization['future_updates'] = future_updates_url
        return response_body_deserialization

    @abstractmethod
    def _get_objects_data(self, objects):
        users_data = []
        for user in objects:
            user_data = {f: getattr(user, f) for f in User.field_names}
            users_data.append(user_data)
        return users_data
