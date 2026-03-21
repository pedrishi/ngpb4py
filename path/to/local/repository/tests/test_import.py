"""Test ngpb4py."""

import ngpb4py


def test_import() -> None:
    """Test that the package can be imported."""
    assert isinstance(ngpb4py.__name__, str)
