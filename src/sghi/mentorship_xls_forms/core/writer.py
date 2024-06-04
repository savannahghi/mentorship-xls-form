from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import override

from sghi.etl.core import Sink
from sghi.exceptions import SGHIError

# =============================================================================
# EXCEPTIONS
# =============================================================================


class WriteError(SGHIError):
    """Error while persisting data."""


# =============================================================================
# WRITER INTERFACE
# =============================================================================


class Writer[_DT](Sink[_DT], metaclass=ABCMeta):
    """
    Interface representing objects that persist processed data to a final
    destination for further consumption by other tools *down stream*.
    """

    __slots__ = ()

    @abstractmethod
    def write(self, data: _DT) -> None:
        """Persist the given data to a destination.

        :param data: The data to persist.

        :return: None.

        :raises WriteError: If an error occurs while persisting, the given
            data.
        """
        ...

    @override
    def drain(self, processed_data: _DT) -> None:
        return self.write(processed_data)
