"""
Shared pytest configuration.

``pythonpath = ["src"]`` in pyproject puts the package on the path, and
``asyncio_mode = strict`` means async tests opt in explicitly with
``@pytest.mark.asyncio``. No global fixtures are needed yet; per-test fixtures
live next to the tests that use them.
"""
