from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Callable

from Framework.abc.Endpoint import ABCEndpoint

T = TypeVar('T')


class ABCStackTracer(ABC, Generic[T]):
    """
    When calculating a stack, the tracer keeps track of all the sub calculations
    """
    @abstractmethod
    def __call__(self, dependency: ABCEndpoint) -> Callable:
        pass

    @abstractmethod
    def reset(self):
        """
        Before each calculation, the results from old runs need to be erased
        """
        pass

    @property
    @abstractmethod
    def intermediates(self) -> T:
        """
        This property is used to store the results from sub calculations
        """
        pass