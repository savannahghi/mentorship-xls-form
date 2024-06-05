from abc import ABCMeta, abstractmethod

# =============================================================================
# INTERFACES
# =============================================================================


class Deserializer[_RT, _PT](metaclass=ABCMeta):
    __slots__ = ()

    def __call__(self, data: _RT) -> _PT:
        return self.deserialize(data)

    @abstractmethod
    def deserialize(self, data: _RT) -> _PT: ...


class Serializer[_PT, _RT](metaclass=ABCMeta):
    __slots__ = ()

    def __call__(self, item: _PT) -> _RT:
        return self.serialize(item)

    @abstractmethod
    def serialize(self, item: _PT) -> _RT: ...
