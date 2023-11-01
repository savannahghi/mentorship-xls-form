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


class WriteError(SGHIError):
    """Error while persisting data."""


# =============================================================================
# WRITER INTERFACE
# =============================================================================


class Writer(Disposable, Generic[_D], metaclass=ABCMeta):
    """
    Interface representing objects that persist processed data to a final
    destination for further consumption by other tools *down stream*.
    """

    __slots__ = ()

    @abstractmethod
    def write(self, data: _D) -> None:
        """Persist the given data to a destination.

        :param data: The data to persist.

        :return: None.

        :raises WriteError: If an error occurs while persisting, the given
            data.
        """
        ...
