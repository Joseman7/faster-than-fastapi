import functools
import inspect
from abc import ABC, abstractmethod
from typing import Callable, Type, OrderedDict, Any

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, create_model
from signedjson.key import generate_signing_key
from signedjson.sign import sign_json
from starlette.responses import JSONResponse

import Framework.warnings as warnings
from Framework.base import InternalException, CalculationModel

SIGNING_KEY = generate_signing_key('test')


def _serialize_warning_header(wng_list):
    delimiter = ";"
    header_str = delimiter.join(map(lambda x: x.message.args[0].__repr__(), wng_list))
    if header_str.count(delimiter) >= len(wng_list):
        raise ValueError('Delimiter is occurring in at least one of the messages!!!')
    return header_str


class DATProDecorator(ABC):

    def __init__(self, fn: Callable):
        self._original_callable = fn
        # print("UPDATED WRAPPER DATA")
        # print(f'WRAPPER ASSIGNMENTS : {functools.WRAPPER_ASSIGNMENTS}')
        # print(f'UPDATES : {functools.WRAPPER_UPDATES}')
        # for x in functools.WRAPPER_ASSIGNMENTS:
        #     print((x, getattr(fn, x)))
        functools.update_wrapper(self, fn, updated=['__annotations__'])

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def original_callable(self) -> Callable:
        return self._original_callable

    @abstractmethod
    def __call__(self, input_model: BaseModel):
        pass


class RuleErrorHandler(DATProDecorator):

    def __call__(self, input_model: BaseModel):
        try:
            res = self.original_callable(input_model)
        except Exception as e:  # catch exceptions in the content owner routine
            return JSONResponse(status_code=567, content=jsonable_encoder(InternalException.from_exception(e)))
        return res


class RuleWarningHandler(DATProDecorator):

    def __call__(self, input_model: BaseModel):
        with warnings.catch_warnings(record=True) as list_wng:
            response_content = self.original_callable(input_model)
            if list_wng:  # Add custom header if warnings have been recorded
                wng_header = {'X-DATPro-Warnings': _serialize_warning_header(list_wng)}
                return JSONResponse(content=jsonable_encoder(response_content), headers=wng_header)
            return response_content


class RuleTraceabilityHandler(DATProDecorator):
    def __init__(self, fn, name):
        sg = inspect.signature(fn)
        return_type_before = sg.return_annotation
        super().__init__(fn)
        self.return_type = create_model(f'{name}Response', input=(sg.parameters['input_model'].annotation, ...),
                                        output=(return_type_before, ...))

    def __call__(self, input_model: BaseModel):
        res = self.original_callable(input_model)
        response_content = self.return_type(input=input_model, output=res)
        return response_content


class RuleSignedHandler(DATProDecorator):
    def __call__(self, input_model: BaseModel):
        res = self.original_callable(input_model)
        sig = sign_json(res.dict(), 'Alice', SIGNING_KEY)
        return self.return_type(**sig)

    def __init__(self, fn, traceable_model: Type[CalculationModel]):
        self.return_type = create_model(traceable_model.__name__,
                                        __base__=traceable_model,
                                        signatures=(dict, ...))
        super().__init__(fn)


class StackTraceabilityHandler(DATProDecorator):
    """
    This function is used to decorate the calculate function of subclasses of ABCStack.
    For traceability reasons, the decorator appends the input data,
        **as well as intermediate data/nested calls** to the response model

    The decorated function is expected to **exactly** one keyword argument "input_model"
    Before the decorated function is called, the tracer result is cleaned up.
    """

    def __init__(self, fn, tracer):
        self.tracer = tracer
        sg = inspect.signature(fn)
        return_type = sg.return_annotation
        dyn_res_model = create_model(f'{tracer.stack.name}Response',
                                     input=(sg.parameters['input_model'].annotation, ...),
                                     intermediates=(OrderedDict[str, Any], ...),
                                     output=(return_type, ...))
        self.return_type = dyn_res_model
        super().__init__(fn)

    def __call__(self, input_model: BaseModel):
        self.tracer.reset()  # Clean tracer
        output = self.original_callable(input_model=input_model)
        if self.tracer.intermediates:
            return self.return_type(input=input_model, output=output, intermediates=self.tracer.intermediates)
        return self.return_type(input=input_model, output=output)
