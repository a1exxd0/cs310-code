# Quickstart for environment setup
Assuming you have [UV](https://docs.astral.sh/uv/) installed:
```sh
uv sync
```

# Run tests
Use parallel workers matching the computer's core count:
```sh
uv run pytest -n auto
```

# Run experiments
Use `--workers` to parallelise with the computer's core count:
```sh
uv run python -m experiments.harness {scaling,bent,truncation,noise,soundness,average_case,gate_noise,all} --workers $(nproc 2>/dev/null || sysctl -n hw.ncpu)
```

# Decode experiment results
```sh
uv run python -m experiments.decode results/scaling_4_10_20.pb
uv run python -m experiments.decode results/scaling_4_10_20.pb -o results/scaling_4_10_20.json
uv run python -m experiments.decode results/*.pb
```

# Local Documentation Build
```sh
uv run sphinx-build docs docs/_build/html
open docs/_build/html/index.html
```
