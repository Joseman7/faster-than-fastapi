from abc import ABC
from typing import Generic

from Framework.base import InModel, OutModel
from Framework.abc.StackTracer import ABCStackTracer
from Framework.abc.Endpoint import ABCEndpoint

from Framework.decorators import StackTraceabilityHandler, RuleSignedHandler, RuleErrorHandler, RuleWarningHandler


class ABCStack(ABCEndpoint, ABC, Generic[InModel, OutModel]):
    """
    The abstract base class for a stack
    Each stack has a tracer that manages/logs the calls to sub calculations
    """
    @property
    def _responses(self) -> dict:
        """
        Use the default responses, but add the ones of the decorated function
        :return:
        """
        return {**super()._responses,
                200: {'model': self.vault[-1][1], 'description': 'Success, inputs, intermediates and outputs'}
                }

    def __init__(self, tracer: ABCStackTracer):
        """
        Store the tracer and initalize the endpoint
        :param tracer:
        """
        self.tracer = tracer
        super().__init__()

    def _decorate_self(self):
        """
        Override the _decorate_self method with Stack specific decorators
        :return:
        """
        rts = StackTraceabilityHandler(fn=self.vault[-1][-1], tracer=self.tracer)
        self.vault.append(("traceable_stack", rts.return_type, rts))
        rsh = RuleSignedHandler(fn=rts, traceable_model=rts.return_type)
        self.vault.append(("signed", rsh.return_type, rsh))
        self.vault.append(("error_handling", self.vault[-1][1], RuleErrorHandler(self.vault[-1][-1])))
        self.vault.append(("warning_handling", self.vault[-1][1], RuleWarningHandler(self.vault[-1][-1])))
        self.calculate = self.vault[-1][-1]  # override the calculate method
