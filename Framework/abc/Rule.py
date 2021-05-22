from abc import ABC
from typing import Generic

from Framework import ABCEndpoint, InModel, OutModel, RuleTraceabilityHandler, RuleSignedHandler, RuleWarningHandler, \
    RuleErrorHandler


class ABCRule(ABCEndpoint, ABC, Generic[InModel, OutModel]):

    def _decorate_self(self):
        rth = RuleTraceabilityHandler(name=self.name, fn=self.vault[-1][-1])
        self.vault.append(("traceable", rth.return_type, rth))
        rsh = RuleSignedHandler(fn=rth, traceable_model=rth.return_type)
        self.vault.append(("signed", rsh.return_type, rsh))
        rwh = RuleWarningHandler(self.vault[-1][-1])
        self.vault.append(("warning_handling", self.vault[-1][1], rwh))
        reh = RuleErrorHandler(self.vault[-1][-1])
        self.vault.append(("error_handling", self.vault[-1][1], reh))
        self.calculate = self.vault[-1][-1]
