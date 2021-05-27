from abc import ABC
from typing import Generic

from Framework import ABCEndpoint, InModel, OutModel, RuleTraceabilityHandler, RuleSignedHandler, RuleWarningHandler, \
    RuleErrorHandler


class ABCRule(ABCEndpoint, ABC, Generic[InModel, OutModel]):

    def _decorate_self(self):
        rth = RuleTraceabilityHandler(original_class=self, name=self.name)
        self.vault.append(("traceable", rth.return_type, rth))
        rsh = RuleSignedHandler(original_class=self, traceable_model=rth.return_type)
        self.vault.append(("signed", rsh.return_type, rsh))
        rwh = RuleWarningHandler(original_class=self)
        self.vault.append(("warning_handling", self.vault[-1][1], rwh))
        reh = RuleErrorHandler(original_class=self)
        self.vault.append(("error_handling", self.vault[-1][1], reh))
        self.calculate = self.vault[-1][-1]
