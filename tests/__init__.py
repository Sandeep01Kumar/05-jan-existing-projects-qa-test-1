"""Test package for the hao-backprop-test Flask service.

This package contains the behavioral-parity test suite that validates
byte-level HTTP-response equivalence between the new Python/Flask service
and the retired Node.js implementation (server.js:L1-L14).

See ``tests/test_app.py`` for parity tests and ``tests/conftest.py`` for
pytest fixtures (``app`` and ``client``).

Per AAP §0.2.1 Test Suite (CREATE), §0.3.1 target-structure tree, and
§0.4.1 transformation row.
"""
