import functools
from typing import Generic, OrderedDict, Callable, Dict, Any, Optional, List, Union

from pydantic import BaseModel, Field

import Framework.warnings as warnings
from Framework.abc.Endpoint import ABCEndpoint
from Framework.abc.Stack import ABCStack
from Framework.abc.StackTracer import ABCStackTracer
from Framework.base import Calculation, InternalException, InModel, OutModel
from Framework.decorators import SIGNING_KEY, _serialize_warning_header, RuleErrorHandler, RuleWarningHandler, \
    RuleTraceabilityHandler, RuleSignedHandler, StackTraceabilityHandler


def setup_logging():
    import logging
    lg = logging.getLogger(__name__)
    lg.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    lg.addHandler(ch)
    return lg


logger = setup_logging()


class Calculations(BaseModel):
    calculations: List[Calculation]


class GenResponseModel(BaseModel, Generic[InModel, OutModel]):
    input: InModel
    intermediates: Optional[Dict[str, 'GenResponseModel']] = Field(default=None)
    output: OutModel


class GenStackModel(GenResponseModel):
    """
    Note that intermediates can be nested!
    """
    intermediates: Optional[Dict[str, Any]] = None


class SimpleStackTracer(ABCStackTracer, OrderedDict[str, BaseModel]):
    """
    This stack tracer provides intermediates as an Ordered Dictionary to preserve the order of the sub calls
    However when calling the same calculation twice on the same level on a stack, it would overwrite the latest entry.
    """
    def __init__(self, stack: ABCStack):
        super().__init__()
        self.stack = stack
        self.dependencies = set()
        self.results = OrderedDict[str, BaseModel]()

    def reset(self):
        self.results = OrderedDict[str, BaseModel]()

    def __call__(self, dependency: Union[ABCStack, ABCEndpoint]) -> Callable:
        self.dependencies.add(dependency)
        # todo: Instead of hard coding, match the signed function
        fn = dependency.vault[2][-1]

        @functools.wraps(fn)
        def inner(input_model: BaseModel):
            logger.info((f'{self.stack.name} is calling {dependency.name}\n'
                          f'...with following data {input_model}'))
            call_result = fn(input_model=input_model)
            if dependency.name in self.results:
                raise KeyError(f'{dependency.name} has already been recorded and should not be overwritten. '
                               f'please use a different type of tracer!')
            self.results[dependency.name] = call_result
            return call_result

        return inner

    @property
    def intermediates(self) -> OrderedDict[str, BaseModel]:
        return self.results
