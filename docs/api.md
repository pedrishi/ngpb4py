# API Reference

## Public Package

::: ngpb4py

## Configuration

::: ngpb4py.config
    options:
      members:
        - PrmOption
        - NgpbConfig
        - packaged_default_input

## Runner

::: ngpb4py.runner
    options:
      members:
        - NgpbRunner

## Results

::: ngpb4py.result
    options:
      members:
        - PotentialSampleSet
        - NgpbResult

## Log Parsing

::: ngpb4py.io.logs
    options:
      members:
        - AxisBounds
        - BoxBounds
        - GridSubdivisions
        - SystemInfo
        - DomainInfo
        - SurfaceBuildInfo
        - GridBuildInfo
        - SolverInfo
        - ElectrostaticEnergy
        - ParsedLog
        - parse_log
        - parse_log_metrics

## PRM Parsing

::: ngpb4py.io.prm
    options:
      members:
        - load_prm
        - render_prm
