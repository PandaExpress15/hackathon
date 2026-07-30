from __future__ import annotations

import pytest

from careerproof.data_loader import load_bundled_dataset


@pytest.fixture(scope="session")
def bundle():
    return load_bundled_dataset()
