import numpy as np
import pytest

from dmsim.ai.model import Model
from dmsim.engine.rustcore import rust_weights


def test_wide_params_are_trimmed_and_valid():
    m = Model(5)
    w = rust_weights(m)
    assert len(w["Wv1"][0]) == 128
    assert len(w["Wc"][0]) == 10 * 64 + 12


def test_bad_shape_raises():
    m = Model(5)
    m.p["Wc"] = m.p["Wc"][:, :100]
    with pytest.raises(ValueError):
        rust_weights(m)
