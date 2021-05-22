# faster-than-fastapi
This project is supposed to show how to easily publish a python function as a microservice.

The target is to give users who have little programming knowledge
the possibility to share calculation rules with others.

As the framework is taking care about decorating of the calculations,
an consistent treatment of all rules shall be ensured,
whereas domain knowledge and responsibilities (microservice architecture vs. calculation) are clearly separated.

## Features
1. For sake of traceability each calculation returns the used inputs on top of the outputs
2. Each calculation response is signed, which makes it possible to identify whether some variables have been modified.
3. Errors are treated in a uniform manner, so that running with malicious data will still return a meaningful error message instead of a Internal Server Error (500)
4. Warnings cascade up to the highest level and are shown in an extra response header.

## Requirements
This repo has been created with Python 3.9
```output
pip install -r requirements.txt
```

## Example
See main.py for some very simple rules.

Run the demonstrator
1. locally using uvicorn
   `uvicorn main:app --reload`
2. executing/debugging main.py

Find the documentation at [http://localhost:8000/docs#/](http://localhost:8000/docs#/)

The docstrings of the input and output models, as well as of the calculate functions will show up in Swagger and
can be formatted by using markdown.

```python
class InputModel(BaseModel):
    """
    Just two numbers as **input**
    """
    x: float = Field(..., example=20)
    y: float = Field(..., example=-3)


class OutputModel(BaseModel):
    """
    And one number as output.

    Magnificent!
    """
    z: float


class Add(ABCRule[InputModel, OutputModel]):
    """
    The visible documentation (Swagger) of this rule is the docstring of the calculate function
    """

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
```

## Background
Heavy lifting is done by [FastAPI](https://fastapi.tiangolo.com/).

Some [abstract base classes](Framework/abc) take care of [decorating](Framework/decorators.py) calculation rules in a uniform manner 
and spinning up a FastAPI application.
There are two classes of rules: Standalone rules and composite rules/stacks.
