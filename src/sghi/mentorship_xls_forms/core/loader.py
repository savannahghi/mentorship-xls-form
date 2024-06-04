from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import override

from sghi.etl.core import Source
from sghi.exceptions import SGHIError

# =============================================================================
# EXCEPTIONS
# =============================================================================


class LoadError(SGHIError):
    """Error while loading metadata from a source."""


# =============================================================================
# LOADER INTERFACE
# =============================================================================


class Loader[_DT](Source[_DT], metaclass=ABCMeta):
    """
    Interface representing objects that read data from a source (or generate
    the data) for further processing or internal consumption by this tool.
    """

    __slots__ = ()

    @abstractmethod
    def load(self) -> _DT:
        """
        Read data from a source and return it for further processing or
        internal consumption.

        :return: The read data.

        :raises LoadError: If an error occurs while reading data from the given
            source.
        """
        ...

    @override
    def draw(self) -> _DT:
        return self.load()
