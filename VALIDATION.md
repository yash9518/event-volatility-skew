# Validation record

Validated locally on October 2, 2026 with Python 3.12.

- 11 unit tests passed (`python -m pytest -q`).
- Research notebook executed end to end: 5 code cells, no error outputs.
- Editable package build and installation succeeded.
- Analysis command executed and report charts visually inspected.
- README and report relative links checked.
- Exact top-level package versions recorded in `requirements-tested.txt`.

Market-data downloads were exercised for the two market projects. Their unit tests use explicit synthetic fixtures, so GitHub CI needs no live market data or secrets. Raw vendor downloads and personal quiz sessions are excluded from Git. The GitHub Actions badge reports remote test status separately.
