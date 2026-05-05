import math

from pydantic import BaseModel, Field


task_specs = {}
task_tests = {}


class ScalarOutput(BaseModel):
    value: float = Field(..., description="The resulting scalar value.")


class PairInputs(BaseModel):
    left: float = Field(..., description="The first number.")
    right: float = Field(..., description="The second number.")


class PositivePairInputs(BaseModel):
    left: float = Field(..., description="A positive number.")
    right: float = Field(..., description="Another positive number.")


class SingleValueInput(BaseModel):
    x: float = Field(..., description="The input value.")


class TripleInputs(BaseModel):
    a: float = Field(..., description="The first number.")
    b: float = Field(..., description="The second number.")
    c: float = Field(..., description="The third number.")


task_specs["task_1"] = {
    "description": "Add left and right and return the result as a single scalar value.",
    "input_model": PairInputs,
    "output_model": ScalarOutput,
}
t1_inputs = [
    PairInputs(left=2, right=5),
    PairInputs(left=-3, right=10),
    PairInputs(left=1.5, right=2.5),
    PairInputs(left=0, right=7),
    PairInputs(left=-8, right=-2),
    PairInputs(left=9, right=1),
    PairInputs(left=100, right=0.5),
    PairInputs(left=12, right=-2),
    PairInputs(left=3.25, right=4.75),
    PairInputs(left=-1.25, right=1.25),
]
t1_outputs = [ScalarOutput(value=i.left + i.right) for i in t1_inputs]
task_tests["task_1"] = {"inputs": t1_inputs, "expected_outputs": t1_outputs}


task_specs["task_2"] = {
    "description": "Subtract right from left and return the difference.",
    "input_model": PairInputs,
    "output_model": ScalarOutput,
}
t2_inputs = [
    PairInputs(left=7, right=2),
    PairInputs(left=5, right=5),
    PairInputs(left=-4, right=3),
    PairInputs(left=9.5, right=1.5),
    PairInputs(left=0, right=2),
    PairInputs(left=20, right=-2),
    PairInputs(left=-8, right=-3),
    PairInputs(left=4.25, right=0.25),
    PairInputs(left=3, right=9),
    PairInputs(left=100, right=33),
]
t2_outputs = [ScalarOutput(value=i.left - i.right) for i in t2_inputs]
task_tests["task_2"] = {"inputs": t2_inputs, "expected_outputs": t2_outputs}


task_specs["task_3"] = {
    "description": "Multiply left and right and return the product.",
    "input_model": PairInputs,
    "output_model": ScalarOutput,
}
t3_inputs = [
    PairInputs(left=3, right=4),
    PairInputs(left=-2, right=5),
    PairInputs(left=1.5, right=2.0),
    PairInputs(left=0, right=10),
    PairInputs(left=-3, right=-7),
    PairInputs(left=8, right=0.5),
    PairInputs(left=12, right=3),
    PairInputs(left=9, right=-1),
    PairInputs(left=2.5, right=2.5),
    PairInputs(left=11, right=11),
]
t3_outputs = [ScalarOutput(value=i.left * i.right) for i in t3_inputs]
task_tests["task_3"] = {"inputs": t3_inputs, "expected_outputs": t3_outputs}


task_specs["task_4"] = {
    "description": "Divide left by right and return the quotient.",
    "input_model": PairInputs,
    "output_model": ScalarOutput,
}
t4_inputs = [
    PairInputs(left=8, right=2),
    PairInputs(left=9, right=3),
    PairInputs(left=7.5, right=2.5),
    PairInputs(left=-12, right=4),
    PairInputs(left=1, right=4),
    PairInputs(left=100, right=5),
    PairInputs(left=-9, right=-3),
    PairInputs(left=3.6, right=1.2),
    PairInputs(left=22, right=11),
    PairInputs(left=81, right=9),
]
t4_outputs = [ScalarOutput(value=i.left / i.right) for i in t4_inputs]
task_tests["task_4"] = {"inputs": t4_inputs, "expected_outputs": t4_outputs}


task_specs["task_5"] = {
    "description": "First add left and right, then square the result.",
    "input_model": PairInputs,
    "output_model": ScalarOutput,
}
t5_inputs = [
    PairInputs(left=2, right=3),
    PairInputs(left=-1, right=4),
    PairInputs(left=1.5, right=0.5),
    PairInputs(left=0, right=7),
    PairInputs(left=-4, right=-2),
    PairInputs(left=10, right=-1),
    PairInputs(left=6, right=6),
    PairInputs(left=3.25, right=1.75),
    PairInputs(left=-8, right=9),
    PairInputs(left=0.5, right=0.5),
]
t5_outputs = [ScalarOutput(value=(i.left + i.right) ** 2) for i in t5_inputs]
task_tests["task_5"] = {"inputs": t5_inputs, "expected_outputs": t5_outputs}


task_specs["task_6"] = {
    "description": "Compute (left + right) multiplied by (left - right).",
    "input_model": PairInputs,
    "output_model": ScalarOutput,
}
t6_inputs = [
    PairInputs(left=7, right=2),
    PairInputs(left=5, right=5),
    PairInputs(left=8, right=3),
    PairInputs(left=1.5, right=0.5),
    PairInputs(left=-4, right=2),
    PairInputs(left=10, right=-1),
    PairInputs(left=3, right=1),
    PairInputs(left=12, right=4),
    PairInputs(left=0.5, right=0.25),
    PairInputs(left=-6, right=-2),
]
t6_outputs = [ScalarOutput(value=(i.left + i.right) * (i.left - i.right)) for i in t6_inputs]
task_tests["task_6"] = {"inputs": t6_inputs, "expected_outputs": t6_outputs}


task_specs["task_7"] = {
    "description": "Return the distance between the two numbers on the real line.",
    "input_model": PairInputs,
    "output_model": ScalarOutput,
}
t7_inputs = [
    PairInputs(left=10, right=4),
    PairInputs(left=-2, right=5),
    PairInputs(left=3, right=3),
    PairInputs(left=1.5, right=2.5),
    PairInputs(left=-10, right=-4),
    PairInputs(left=7, right=-1),
    PairInputs(left=0, right=9),
    PairInputs(left=2.25, right=0.25),
    PairInputs(left=-8, right=1),
    PairInputs(left=4, right=11),
]
t7_outputs = [ScalarOutput(value=abs(i.left - i.right)) for i in t7_inputs]
task_tests["task_7"] = {"inputs": t7_inputs, "expected_outputs": t7_outputs}


task_specs["task_8"] = {
    "description": "Compute sin(x)^2 plus cos(x)^2 for the provided x.",
    "input_model": SingleValueInput,
    "output_model": ScalarOutput,
}
t8_inputs = [SingleValueInput(x=x) for x in [0.0, 0.5, 1.2, -0.7, 2.4, math.pi / 3, math.pi / 2, 3.0, -2.5, 4.1]]
t8_outputs = [ScalarOutput(value=1.0) for _ in t8_inputs]
task_tests["task_8"] = {"inputs": t8_inputs, "expected_outputs": t8_outputs}


task_specs["task_9"] = {
    "description": "Compute the geometric mean of two positive numbers by multiplying them first and then taking the square root.",
    "input_model": PositivePairInputs,
    "output_model": ScalarOutput,
}
t9_inputs = [
    PositivePairInputs(left=4, right=9),
    PositivePairInputs(left=1, right=16),
    PositivePairInputs(left=2.25, right=4),
    PositivePairInputs(left=3, right=12),
    PositivePairInputs(left=0.25, right=4),
    PositivePairInputs(left=6, right=24),
    PositivePairInputs(left=5, right=20),
    PositivePairInputs(left=1.5, right=6),
    PositivePairInputs(left=10, right=40),
    PositivePairInputs(left=2, right=8),
]
t9_outputs = [ScalarOutput(value=math.sqrt(i.left * i.right)) for i in t9_inputs]
task_tests["task_9"] = {"inputs": t9_inputs, "expected_outputs": t9_outputs}


task_specs["task_10"] = {
    "description": "Return the derivative of x squared evaluated at x.",
    "input_model": SingleValueInput,
    "output_model": ScalarOutput,
}
t10_inputs = [SingleValueInput(x=x) for x in [4, -1.5, 0, 2.25, -3, 7, 0.5, -8, 10, 1.2]]
t10_outputs = [ScalarOutput(value=2 * i.x) for i in t10_inputs]
task_tests["task_10"] = {"inputs": t10_inputs, "expected_outputs": t10_outputs}


task_specs["task_11"] = {
    "description": "Return the derivative of x cubed plus sine of x evaluated at x.",
    "input_model": SingleValueInput,
    "output_model": ScalarOutput,
}
t11_inputs = [SingleValueInput(x=x) for x in [2.0, 0.0, -1.0, 1.5, math.pi / 2, -2.5, 3.0, 0.25, -4.0, 5.0]]
t11_outputs = [ScalarOutput(value=3 * (i.x ** 2) + math.cos(i.x)) for i in t11_inputs]
task_tests["task_11"] = {"inputs": t11_inputs, "expected_outputs": t11_outputs}


task_specs["task_12"] = {
    "description": "Multiply two positive numbers, but do it through logarithms and exponentiation rather than a direct multiply tool.",
    "input_model": PositivePairInputs,
    "output_model": ScalarOutput,
}
t12_inputs = [
    PositivePairInputs(left=2.0, right=8.0),
    PositivePairInputs(left=1.5, right=4.0),
    PositivePairInputs(left=3.0, right=9.0),
    PositivePairInputs(left=0.5, right=6.0),
    PositivePairInputs(left=10.0, right=2.0),
    PositivePairInputs(left=4.0, right=4.0),
    PositivePairInputs(left=1.25, right=8.0),
    PositivePairInputs(left=7.0, right=3.0),
    PositivePairInputs(left=2.5, right=2.0),
    PositivePairInputs(left=12.0, right=0.5),
]
t12_outputs = [ScalarOutput(value=i.left * i.right) for i in t12_inputs]
task_tests["task_12"] = {"inputs": t12_inputs, "expected_outputs": t12_outputs}


task_specs["task_13"] = {
    "description": "Compute the normalized radius sqrt(a squared plus b squared) divided by the magnitude of c.",
    "input_model": TripleInputs,
    "output_model": ScalarOutput,
}
t13_inputs = [
    TripleInputs(a=3.0, b=4.0, c=-2.0),
    TripleInputs(a=5.0, b=12.0, c=13.0),
    TripleInputs(a=8.0, b=15.0, c=-5.0),
    TripleInputs(a=6.0, b=8.0, c=10.0),
    TripleInputs(a=1.5, b=2.0, c=-0.5),
    TripleInputs(a=7.0, b=24.0, c=5.0),
    TripleInputs(a=9.0, b=12.0, c=-3.0),
    TripleInputs(a=4.0, b=3.0, c=2.5),
    TripleInputs(a=10.0, b=24.0, c=-2.0),
    TripleInputs(a=0.6, b=0.8, c=0.5),
]
t13_outputs = [
    ScalarOutput(value=math.sqrt((i.a ** 2) + (i.b ** 2)) / abs(i.c))
    for i in t13_inputs
]
task_tests["task_13"] = {"inputs": t13_inputs, "expected_outputs": t13_outputs}


task_specs["task_14"] = {
    "description": "Build a cubic interaction score by adding a and b, cubing the result, and dividing by the magnitude of c.",
    "input_model": TripleInputs,
    "output_model": ScalarOutput,
}
t14_inputs = [
    TripleInputs(a=1.0, b=2.0, c=-3.0),
    TripleInputs(a=2.0, b=1.0, c=9.0),
    TripleInputs(a=3.0, b=3.0, c=-6.0),
    TripleInputs(a=0.5, b=1.5, c=2.0),
    TripleInputs(a=-1.0, b=4.0, c=-3.0),
    TripleInputs(a=5.0, b=-2.0, c=3.0),
    TripleInputs(a=2.5, b=2.5, c=-5.0),
    TripleInputs(a=4.0, b=1.0, c=2.5),
    TripleInputs(a=6.0, b=-3.0, c=-9.0),
    TripleInputs(a=1.2, b=0.8, c=0.5),
]
t14_outputs = [
    ScalarOutput(value=((i.a + i.b) ** 3) / abs(i.c))
    for i in t14_inputs
]
task_tests["task_14"] = {"inputs": t14_inputs, "expected_outputs": t14_outputs}


task_specs["task_15"] = {
    "description": "Compute tangent of x by dividing sine of x by cosine of x.",
    "input_model": SingleValueInput,
    "output_model": ScalarOutput,
}
t15_inputs = [SingleValueInput(x=x) for x in [0.25, 0.5, 1.0, -0.75, 1.2, -1.1, 0.9, -0.3, 0.7, -0.6]]
t15_outputs = [ScalarOutput(value=math.tan(i.x)) for i in t15_inputs]
task_tests["task_15"] = {"inputs": t15_inputs, "expected_outputs": t15_outputs}
