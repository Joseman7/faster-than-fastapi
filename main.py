"""
This module contains the rules/stacks from the content owner perspective
"""

from pydantic import BaseModel, Field

import uvicorn
import Framework.warnings as warnings

from Framework import ABCEndpoint, ABCStack, SimpleStackTracer
from Framework.abc.Rule import ABCRule


class InputModel(BaseModel):
    """
    Just two numbers as **input**
    """
    x: float = Field(..., example=20, mapping="ABC")
    y: float = Field(..., example=-3)


class OutputModel(BaseModel):
    """
    And one number as output.

    Magnificent!
    """
    z: float


class Add(ABCRule[InputModel, OutputModel], tag="SimpleCalculations"):
    """
    The visible documentation (Swagger) of this rule is the docstring of the calculate function
    """
    owner = "Another"

    def calculate(self, input_model: InputModel) -> OutputModel:
        """
        To calculate the sum. Have fun with it.
        """
        z = input_model.x + input_model.y
        if input_model.x == 4:
            raise ValueError(f"We don't like the number 4")
            # warnings.warn(ValueError(f"We don't like the number 4"))
        warnings.warn('Actually, we are really picky')
        return OutputModel(z=z)


class Subtract(ABCRule[InputModel, OutputModel], tag="SimpleCalculations"):
    owner = "A third"

    def calculate(self, input_model: InputModel) -> OutputModel:
        """
        To calculate a **difference**.
        Here's a [LINK](google.com)
        # References
        It's a reference, for god's sake!
        """
        z = input_model.x - input_model.y
        return OutputModel(z=z)


class MyFirstStack(ABCStack[InputModel, OutputModel]):
    """
    A demonstrator to show how a stack works
    """
    def __init__(self, add=Add(), subtract=Subtract()):
        sst = SimpleStackTracer(self)
        super().__init__(sst)
        self.add = sst(add)
        self.subtract = sst(subtract)

    def calculate(self, input_model: InputModel) -> OutputModel:
        """
        We take two input parameters and add them
        then we subtract 5 from the result and subtract the second variable (y)
        """
        res1 = self.add(input_model)
        res2 = self.subtract(InputModel(x=res1.output.z - 5, y=input_model.y))
        return OutputModel(z=res2.output.z)


class NestedStack(ABCStack[InputModel, OutputModel]):
    """
    A demonstrator to show that it is possible to deeply nest stacks
    """
    def __init__(self, stack=MyFirstStack(), subtract=Subtract()):
        sst = SimpleStackTracer(self)
        super().__init__(sst)

        self.stack = sst(stack)
        self.subtract = sst(subtract)

    def calculate(self, input_model: InputModel) -> OutputModel:
        """
        Run the SimpleStack and then subtract 5 from that result and further subtract the second variable
        """
        res1 = self.stack(input_model)
        res2 = self.subtract(InputModel(x=res1.output.z - 5, y=input_model.y))
        return OutputModel(z=res2.output.z)


if __name__ == '__main__':
    app = ABCEndpoint.main_app()
    uvicorn.run(app, host="127.0.0.1", port=8000)
