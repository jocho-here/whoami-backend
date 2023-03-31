from enum import Enum


class FollowingStatus(str, Enum):
    FOLLOWING = "following"
    NOT_FOLLOWING = "not_following"
    REQUESTED = "requested"
