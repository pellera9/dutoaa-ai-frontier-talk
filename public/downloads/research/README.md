# Opening example: latent-space Gamma research audit

The canonical standalone reference and runnable program are at the repository root:
`latent_space_zig_explained.md` and `latent_space_zig_xgboost.py`.
The public reader is generated from that reference; do not edit its generated copy.

## Run

```bash
python3 -m venv .venv-zig
source .venv-zig/bin/activate
python3 -m pip install -r research/latent-space-zig/requirements.txt
python3 latent_space_zig_xgboost.py --tests-only
python3 latent_space_zig_xgboost.py --self-test
python3 latent_space_zig_xgboost.py --self-test --scenario gamma-power --output research/latent-space-zig/results-gamma-power
```

Use Python 3.12 or newer. Dependencies are pinned to the versions used for the recorded runs.
Default: 5,000 synthetic observations, seed 20261003, 60/20/20 split, cap 100,000,
maximum 250 rounds. Structural parameters use training data; validation selects stopping
and Tweedie power. The test set is reserved for final reporting.

## Artifacts and interpretation

- `metrics.json`: configuration, versions, structural candidates, checks, metrics, base margins.
- `comparison.csv`: four-model comparison on the same held-out data.
- `test-predictions.csv`: synthetic row-level predictions; no real insurance data.
- `*.ubj`: fitted example boosters. Inference also needs the structure/base margins and feature schema in the program and JSON.
- `*.svg`: original transformation/Newton and calibration plots.

The public package includes the code, reference, requirements, summaries and plots.
Model files and row-level predictions stay in the private source repository.
The original paper PDF and all narration audio are excluded from the public package.

This is an independent educational implementation, not the paper author's code.
The main fixed-structure derivatives and bounded expectation passed numerical checks.
Counterexamples invalidate two unrestricted deviance/profiling claims; the program uses
censoring-aware likelihood estimation instead. Neither synthetic scenario establishes
consistent superiority. Both null calibrations selected the lower lambda-grid boundary:
inspect sensitivity before interpreting fitted parameters or using real data.

## Extending the experiment

```bash
python3 latent_space_zig_xgboost.py --self-test --cap 50000 --lambda-grid .05,.1,.15,.25,.4,.6,.85 --output /tmp/zig-sensitivity
```

Use repeated seeds and multiple caps, widen/refine the structural search, compare conditional
calibration, and validate on appropriately governed real datasets before production use.
The generated comparison is a demonstration, not insurance pricing advice.
