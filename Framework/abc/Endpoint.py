import inspect
from abc import ABC, abstractmethod
from typing import Generic, List

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
    todo: better to split responsibilites?!
    """
    rules = set()

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
                response_description="Provides name and endpoint of the available calculations")\
            (cls.list_calculations)
        for rule in cls.rules:
            r: ABCEndpoint = rule()
            app.include_router(r.app, prefix="/" + r.name, tags=[r.name])
        return app

    @abstractmethod
    def calculate(self, input_model: InModel) -> OutModel:
        """
        To be overriden by concrete subclasses (content owner)
        """
        pass

    @abstractmethod
    def _decorate_self(self):
        """
        To be overriden by abstract subclasses like ABCRule or ABCStack
        Shall decorates standalone rules or stacks
        Is called automatically when instantiating a concrete subclass
        Intended to modify self.vault with sequential decorations of the calculation function
        """
        pass

    @property
    def _app_kwargs(self) -> dict:
        """
        This method is used to provide data for FastAPI / Swagger
        """
        # set a default path suffix for each calculation endpoint
        ret = {'path': "/calculate/"}
        if isinstance(self._responses, dict):
            ret['responses'] = self._responses
        # Obtain the response model of the calculation function after the last decoration
        ret['response_model'] = self.vault[-1][1]
        ret['summary'] = "Not sure what to put here yet..."
        return ret

    @property
    def _responses(self) -> dict:
        """
        This method is used to add some response types that are common over all services
        """
        return {
            567: {'description': 'An error has been thrown in the internal calculation. Blame the content owner!',
                  'model': InternalException}
        }

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
        # decorate self will modify self.vault
        self._decorate_self()
        # initialize the endpoint
        self.app = APIRouter()
        self.app.post(**self._app_kwargs)(self.calculate)
