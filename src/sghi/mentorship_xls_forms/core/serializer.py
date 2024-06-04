from abc import ABCMeta, abstractmethod

# =============================================================================
# INTERFACES
# =============================================================================


class Deserializer[_RT, _PT](metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def deserialize(self, data: _RT) -> _PT: ...


class Serializer[_PT, _RT](metaclass=ABCMeta):
    __slots__ = ()

    @abstractmethod
    def serialize(self, item: _PT) -> _RT: ...
