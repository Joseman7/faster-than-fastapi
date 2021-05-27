import inspect
from abc import ABC, abstractmethod
from typing import Generic, List, get_args

from fastapi import FastAPI, APIRouter

from Framework.base import InModel, OutModel, Calculation, InternalException


class ABCEndpoint(ABC, Generic[InModel, OutModel]):
    """
    This abstract class is used to
     - keep track of all subclasses (via __init_subclass__)
     - provide the list of subclasses for Swagger (via calculations)
     - provide a local http server (via main_app)
     - enforce subclasses to implement the calculate method (@abstractmethod)
     - decorate subclasses via __init__, which must be called when instantiating a concrete subclass via super
    todo: better to split responsibilities?!
    """
    rules = set()
    owner = "SomeOwner"
    _endpoint_kwargs = dict()

    def __init_subclass__(cls, **kwargs):
        """
        This hook is used to register concrete subclasses e.g. Rules/Stacks
        Each concrete class implementing the ABCEndpoint should be created/defined only once
        """
        class_already_registered = cls.__name__ in {r.__name__ for r in ABCEndpoint.rules}
        class_is_abstract = ABC in cls.__bases__
        if not class_is_abstract and class_already_registered:
            raise KeyError(f'{cls} has already been registered, please choose a unique class name!')
        elif not class_is_abstract:
            ABCEndpoint.rules.add(cls)
            cls._populate_class_variables(kwargs)

    @classmethod
    def _populate_class_variables(cls, kwargs):
        cls.tag = kwargs.pop('tag', cls.__name__)
        cls.summary = kwargs.pop('summary', "Not sure what to put here yet...")
        for key, value in kwargs:
            setattr(cls, key, value)

    @classmethod
    def list_calculations(cls):
        """
        The function that returns the list of calculations
        """
        return [Calculation(name=rule.__name__, endpoint="/" + rule.__name__) for rule in cls.rules]

    @classmethod
    def main_app(cls):
        """
        This method is used to spin up FastAPI
        First, provide the method to list all available/concrete calculations
        Secondly, mount all available/concrete endpoints
        :return: app that can be served with uvicorn
        """
        app = FastAPI(title="System")
        app.get("/calculations",
                response_model=List[Calculation],
                summary="List available calculations",
                response_description="Provides name and endpoint of the available calculations",
                tags=['top-level'])(cls.list_calculations)
        for rule in cls.rules:
            r: ABCEndpoint = rule()
            app.include_router(r.app, tags=[r.tag])
        return app

    @abstractmethod
    def calculate(self, input_model: InModel) -> OutModel:
        """
        To be overridden by concrete subclasses (content owner)
        """
        pass

    @abstractmethod
    def _decorate_self(self):
        """
        To be overridden by abstract subclasses like ABCRule or ABCStack
        Shall decorates standalone rules or stacks
        Is called automatically when instantiating a concrete subclass
        Intended to modify self.vault with sequential decorations of the calculation function
        """
        pass

    def init_endpoint_kwargs(self):
        """
        This method is used to provide data for FastAPI / Swagger
        """
        # set a default path suffix for each calculation endpoint
        ret = {'path': "/" + self.name}
        if isinstance(self._responses, dict):
            ret['responses'] = self._responses
        # Obtain the response model of the calculation function after the last decoration
        ret['response_model'] = self.vault[-1][1]
        ret['summary'] = self.summary
        self._endpoint_kwargs.update(ret)

    def update_endpoint_kwargs(self, **values):
        self._endpoint_kwargs.update(values)

    @property
    def _responses(self) -> dict:
        """
        This method is used to add some response types that are common over all services
        """
        return {
            567: {'description': 'An error has been thrown in the internal calculation. Blame the content owner!',
                  'model': InternalException}
        }

    @property
    def input_model(self) -> InModel:
        return get_args(self.__orig_bases__[0])[0]

    def input_schema(self):
        return self.input_model.schema()

    def mapping(self):
        return {name: field.field_info.extra.get('mapping') for name, field in self.input_model.__fields__.items()
                if field.field_info.extra.get('mapping')}

    def __init__(self):
        """
        Init is called when instantiating the concrete subclasses (rules/stacks/...)
        """
        self.name = self.__class__.__name__  # Use the name of the child class as the name
        """
        vault contains a sequence of tuples ("name", return type, (decorated) function)
        each decoration adds an element to this sequence
        """
        self.vault = [("original", inspect.signature(self.calculate).return_annotation, self.calculate)]
        self.init_endpoint_kwargs()
        # decorate self will modify self.vault
        self._decorate_self()
        self.init_endpoint_kwargs()
        # initialize the endpoint
        self.app = APIRouter()
        self.app.get(self._endpoint_kwargs.get('path', '') + "/schema", summary=f'Obtain the input_schema')(
            self.input_schema)
        self.app.get(self._endpoint_kwargs.get('path', '') + "/mapping", summary=f'Obtain mappings')(self.mapping)
        self.app.post(**self._endpoint_kwargs)(self.calculate)
