"""Validate every corpus case against the JSON schema.

Usage: python tools/validate_corpus.py [paths...]
"""
import json
import sys
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "corpus/schema/case.schema.json").read_text())


def validate(path: Path) -> list[str]:
    try:
        case = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        return [f"YAML syntax: {e}".replace("\n", " ")]
    validator = jsonschema.Draft202012Validator(SCHEMA)
    errors = [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in validator.iter_errors(case)]
    if isinstance(case, dict) and case.get("id") != path.stem:
        errors.append(f"id {case.get('id')!r} does not match filename {path.stem!r}")
    return errors


def main(argv: list[str]) -> int:
    paths = [Path(p) for p in argv] or sorted((ROOT / "corpus/cases").glob("*.yaml"))
    bad = 0
    for p in paths:
        errs = validate(p)
        if errs:
            bad += 1
            print(f"FAIL {p.name}")
            for e in errs:
                print(f"  {e}")
        else:
            print(f"ok   {p.name}")
    print(f"{len(paths) - bad}/{len(paths)} valid")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
