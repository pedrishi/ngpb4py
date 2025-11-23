"""ngpb4py - Pythonic wrapper for NextGenPB."""

from ngpb4py.exceptions import ParameterError
from ngpb4py.ngpb4py import NGPB
from ngpb4py.parameters import (
    ElectrostaticsParameters,
    InputParameters,
    MeshParameters,
    OutputParameters,
    SolverParameters,
    SurfaceParameters,
)

__version__ = "0.1.0"

__all__ = [
    "NGPB",
    "ElectrostaticsParameters",
    "InputParameters",
    "MeshParameters",
    "OutputParameters",
    "ParameterError",
    "SolverParameters",
    "SurfaceParameters",
]
