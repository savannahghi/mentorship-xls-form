from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar

from sghi.disposable import Disposable
from sghi.exceptions import SGHIError

# =============================================================================
# TYPES
# =============================================================================

_D = TypeVar("_D")


# =============================================================================
# EXCEPTIONS
# =============================================================================


class LoadError(SGHIError):
    """Error while loading metadata from a source."""


# =============================================================================
# LOADER INTERFACE
# =============================================================================


class Loader(Disposable, Generic[_D], metaclass=ABCMeta):
    """
    Interface representing objects that read data from a source (or generate
    the data) for further processing or internal consumption by this tool.
    """

    __slots__ = ()

    @abstractmethod
    def load(self) -> _D:
        """
        Read data from a source and return it for further processing or
        internal consumption.

        :return: The read data.

        :raises LoadError: If an error occurs while reading data from the given
            source.
        """
        ...
