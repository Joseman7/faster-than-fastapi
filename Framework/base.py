from typing import TypeVar, Generic, Optional, List

from pydantic import BaseModel
from pydantic.generics import GenericModel


class Calculation(BaseModel):
    name: str
    endpoint: str


class InternalException(BaseModel):
    msg: str
    exception_type: str = None

    @classmethod
    def from_exception(cls, e: Exception):
        return cls(msg=str(e), exception_type=type(e).__name__)


InModel = TypeVar('InModel', bound=BaseModel)
OutModel = TypeVar('OutModel', bound=BaseModel)


class CalculationModel(GenericModel, Generic[InModel, OutModel]):
    input: InModel
    output: OutModel
    warnings: Optional[List[str]] = None
