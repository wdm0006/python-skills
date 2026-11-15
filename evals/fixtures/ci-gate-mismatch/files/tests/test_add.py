import os

from sample_pkg import add


def test_add():
    assert add(1, 2) == 3
