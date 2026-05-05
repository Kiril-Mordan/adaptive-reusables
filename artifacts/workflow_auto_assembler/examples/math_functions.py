import math

from pydantic import BaseModel, Field


class UnaryNumberInput(BaseModel):
    x: float = Field(..., description="A real-valued input number.")


class BinaryNumberInput(BaseModel):
    left: float = Field(..., description="The first input number.")
    right: float = Field(..., description="The second input number.")


class PowerInput(BaseModel):
    base: float = Field(..., description="The numeric base.")
    exponent: float = Field(..., description="The numeric exponent.")


class ScalarOutput(BaseModel):
    value: float = Field(..., description="The resulting scalar value.")


def add(inputs: BinaryNumberInput) -> ScalarOutput:
    """Add two numbers."""
    return ScalarOutput(value=inputs.left + inputs.right)


def subtract(inputs: BinaryNumberInput) -> ScalarOutput:
    """Subtract the second number from the first."""
    return ScalarOutput(value=inputs.left - inputs.right)


def multiply(inputs: BinaryNumberInput) -> ScalarOutput:
    """Multiply two numbers."""
    return ScalarOutput(value=inputs.left * inputs.right)


def divide(inputs: BinaryNumberInput) -> ScalarOutput:
    """Divide the first number by the second."""
    return ScalarOutput(value=inputs.left / inputs.right)


def power(inputs: PowerInput) -> ScalarOutput:
    """Raise a base to a given exponent."""
    return ScalarOutput(value=inputs.base ** inputs.exponent)


def square(inputs: UnaryNumberInput) -> ScalarOutput:
    """Square a number."""
    return ScalarOutput(value=inputs.x ** 2)


def cube(inputs: UnaryNumberInput) -> ScalarOutput:
    """Cube a number."""
    return ScalarOutput(value=inputs.x ** 3)


def reciprocal(inputs: UnaryNumberInput) -> ScalarOutput:
    """Return the reciprocal of a number."""
    return ScalarOutput(value=1 / inputs.x)


def absolute_value(inputs: UnaryNumberInput) -> ScalarOutput:
    """Return the absolute value of a number."""
    return ScalarOutput(value=abs(inputs.x))


def negate(inputs: UnaryNumberInput) -> ScalarOutput:
    """Negate a number."""
    return ScalarOutput(value=-inputs.x)


def square_root(inputs: UnaryNumberInput) -> ScalarOutput:
    """Compute the principal square root of a non-negative number."""
    return ScalarOutput(value=math.sqrt(inputs.x))


def natural_log(inputs: UnaryNumberInput) -> ScalarOutput:
    """Compute the natural logarithm of a positive number."""
    return ScalarOutput(value=math.log(inputs.x))


def exponential(inputs: UnaryNumberInput) -> ScalarOutput:
    """Compute e raised to a number."""
    return ScalarOutput(value=math.exp(inputs.x))


def sine(inputs: UnaryNumberInput) -> ScalarOutput:
    """Compute the sine of a number in radians."""
    return ScalarOutput(value=math.sin(inputs.x))


def cosine(inputs: UnaryNumberInput) -> ScalarOutput:
    """Compute the cosine of a number in radians."""
    return ScalarOutput(value=math.cos(inputs.x))


def tangent(inputs: UnaryNumberInput) -> ScalarOutput:
    """Compute the tangent of a number in radians."""
    return ScalarOutput(value=math.tan(inputs.x))


def derivative_square(inputs: UnaryNumberInput) -> ScalarOutput:
    """Return the derivative of x^2 evaluated at x."""
    return ScalarOutput(value=2 * inputs.x)


def derivative_cube(inputs: UnaryNumberInput) -> ScalarOutput:
    """Return the derivative of x^3 evaluated at x."""
    return ScalarOutput(value=3 * (inputs.x ** 2))


def derivative_sine(inputs: UnaryNumberInput) -> ScalarOutput:
    """Return the derivative of sin(x) evaluated at x."""
    return ScalarOutput(value=math.cos(inputs.x))


def derivative_cosine(inputs: UnaryNumberInput) -> ScalarOutput:
    """Return the derivative of cos(x) evaluated at x."""
    return ScalarOutput(value=-math.sin(inputs.x))
