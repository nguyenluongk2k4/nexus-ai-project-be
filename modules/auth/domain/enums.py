from enum import Enum

class ForumRank(str, Enum):
    MEMBER = "Member"
    JUNIOR = "Junior"
    MIDDLE = "Middle"
    SENIOR = "Senior"
    EXPERT = "Expert"

    @classmethod
    def from_points(cls, points: int) -> "ForumRank":
        if points >= 10000:
            return cls.EXPERT
        if points >= 3000:
            return cls.SENIOR
        if points >= 1000:
            return cls.MIDDLE
        if points >= 200:
            return cls.JUNIOR
        return cls.MEMBER
