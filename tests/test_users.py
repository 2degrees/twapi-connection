from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty
from inspect import isgenerator
from itertools import islice

from nose.tools import eq_

from twapi.testing import MockConnection
from twapi.testing import SuccessfulAPICall
from twapi.users import BATCH_RETRIEVAL_SIZE_LIMIT
from twapi.users import Group
from twapi.users import User
from twapi.users import get_deleted_users
from twapi.users import get_group_members
from twapi.users import get_groups
from twapi.users import get_users


class _ObjectsRetrievalTestCase(object, metaclass=ABCMeta):

    _DATA_RETRIEVER = abstractproperty()

    _SIMULATOR = abstractproperty()

    def test_no_data(self):
        self._test_retrieved_objects(0)

    def test_not_exceeding_pagination_size(self):
        self._test_retrieved_objects(BATCH_RETRIEVAL_SIZE_LIMIT - 1)

    def test_exceeding_pagination_size(self):
        self._test_retrieved_objects(BATCH_RETRIEVAL_SIZE_LIMIT + 1)

    def _test_retrieved_objects(self, count):
        objects = self._generate_deserialized_objects(count)
        simulator = self._make_simulator(objects)
        with MockConnection(simulator) as connection:
            data = self._retrieve_data(connection)
            retrieved_objects = list(data)
        eq_(objects, retrieved_objects)

    def _retrieve_data(self, connection):
        return self._DATA_RETRIEVER(connection)

    def _make_simulator(self, objects):
        return self._SIMULATOR(objects)

    @abstractmethod
    def _generate_deserialized_objects(self, count):
        pass


class _PaginatedObjectsRetriever(object, metaclass=ABCMeta):

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

    def _get_objects_data(self, objects):
        return objects


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


class _GetUsers(_PaginatedObjectsRetriever):
    """Simulator for a successful call to :func:`~twapi.get_users`."""

    _API_CALL_PATH_INFO = '/users/'

    def _get_objects_data(self, objects):
        users_data = []
        for user in objects:
            user_data = {f: getattr(user, f) for f in User.field_names}
            users_data.append(user_data)
        return users_data


class _GetDeletedUsers(_PaginatedObjectsRetriever):
    """Simulator for a successful call to :func:`~twapi.get_deleted_users`."""

    _API_CALL_PATH_INFO = '/users/deleted/'


class _GetGroups(_PaginatedObjectsRetriever):
    """Simulator for a successful call to :func:`~twapi.get_groups`."""

    _API_CALL_PATH_INFO = '/groups/'

    def _get_objects_data(self, objects):
        groups_data = []
        for group in objects:
            group_data = {f: getattr(group, f) for f in Group.field_names}
            groups_data.append(group_data)
        return groups_data


class _GetGroupMembers(_PaginatedObjectsRetriever):
    """Simulator for a successful call to :func:`~twapi.get_group_members`."""

    def __init__(self, objects, group_id):
        super(_GetGroupMembers, self).__init__(objects)

        self._group_id = group_id

    @property
    def _API_CALL_PATH_INFO(self):
        return '/groups/{}/members/'.format(self._group_id)


class TestUsersRetrieval(_ObjectsRetrievalTestCase):

    _DATA_RETRIEVER = staticmethod(get_users)

    _SIMULATOR = staticmethod(_GetUsers)

    @staticmethod
    def _generate_deserialized_objects(count):
        users = []
        for counter in range(count):
            user = User(
                id=counter,
                full_name='User {}'.format(counter),
                email_address='user-{}@example.com'.format(counter),
                organization_name='Example Ltd',
                job_title='Employee {}'.format(counter),
                )
            users.append(user)
        return users


class TestDeletedUsersRetrieval(_ObjectsRetrievalTestCase):

    _DATA_RETRIEVER = staticmethod(get_deleted_users)

    _SIMULATOR = staticmethod(_GetDeletedUsers)

    @staticmethod
    def _generate_deserialized_objects(count):
        return list(range(count))


class TestGroupsRetrieval(_ObjectsRetrievalTestCase):

    _DATA_RETRIEVER = staticmethod(get_groups)

    _SIMULATOR = staticmethod(_GetGroups)

    @staticmethod
    def _generate_deserialized_objects(count):
        groups = [Group(id=i) for i in range(count)]
        return groups


class TestGroupMembersRetrieval(_ObjectsRetrievalTestCase):

    _DATA_RETRIEVER = staticmethod(get_group_members)

    _SIMULATOR = staticmethod(_GetGroupMembers)

    _GROUP_ID = 1

    def _retrieve_data(self, connection):
        return self._DATA_RETRIEVER(connection, self._GROUP_ID)

    def _make_simulator(self, objects):
        return self._SIMULATOR(objects, self._GROUP_ID)

    @staticmethod
    def _generate_deserialized_objects(count):
        return list(range(count))
