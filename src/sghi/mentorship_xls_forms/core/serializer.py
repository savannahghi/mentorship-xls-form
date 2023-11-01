from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar

# =============================================================================
# TYPES
# =============================================================================

_P = TypeVar("_P")
_R = TypeVar("_R")


# =============================================================================
# INTERFACES
# =============================================================================


class Deserializer(Generic[_R, _P], metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def deserialize(self, data: _R) -> _P:
        ...


class Serializer(Generic[_P, _R], metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def serialize(self, item: _P) -> _R:
        ...
