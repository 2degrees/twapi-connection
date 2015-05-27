"""Cross-Domain Authentication"""
from twapi.exc import NotFoundError


class AccessTokenError(NotFoundError):
    pass


def claim_access_token(connection, access_token):
    """
    Claim the session identified by access_token and return the associated
    user’s Id (integer).

    """
    path_info = '/sessions/{}/'.format(access_token)
    try:
        user_id = connection.send_post_request(path_info)
    except NotFoundError:
        raise AccessTokenError()

    return user_id


def is_session_active(connection, access_token):
    """Check whether the session identified by access_token is still active."""

    path_info = '/sessions/{}/'.format(access_token)
    try:
        connection.send_head_request(path_info)
    except NotFoundError:
        is_active = False
    else:
        is_active = True

    return is_active
