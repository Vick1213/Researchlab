from pathlib import Path

import pytest

from tools.validate_corpus import ROOT, validate

CASES = sorted((ROOT / "corpus/cases").glob("*.yaml"))


@pytest.mark.parametrize("path", CASES, ids=[p.stem for p in CASES])
def test_case_validates(path: Path):
    assert validate(path) == []
