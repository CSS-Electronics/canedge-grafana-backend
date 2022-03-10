from enum import Enum, auto, IntEnum


class CanedgeInterface(Enum):

    def __str__(self):
        return str(self.name)

    CAN = auto()
    LIN = auto()


class CanedgeChannel(IntEnum):

    def __str__(self):
        return str(self.name)

    CH1 = 1
    CH2 = 2


class SampleMethod(IntEnum):

    def __str__(self):
        return str(self.name)

    NEAREST = auto()
    MAX = auto()
    MIN = auto()
