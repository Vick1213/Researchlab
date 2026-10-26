"""Generate the obfuscated variant: a fictional system whose period-distance exponent
is not 3/2, so recalling Kepler's law gives the wrong answer.

Run once; the outputs are committed so runs are reproducible.
    python tasks/kepler_third_law/make_synthetic.py
"""
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).parent
SEED = 20261026
EXPONENT = 1.25  # T = C * r**1.25, i.e. T**4 proportional to r**5
NOISE = 0.002    # lognormal measurement noise on the period


def make(rng, n, c, r_lo, r_hi, prefix):
    r = np.sort(np.exp(rng.uniform(np.log(r_lo), np.log(r_hi), n)))
    t = c * r**EXPONENT * np.exp(rng.normal(0, NOISE, n))
    return [(f"{prefix}-{i + 1}", round(float(ti), 4), round(float(ri), 4)) for i, (ti, ri) in enumerate(zip(t, r))]


def write(path, rows):
    with open(path, "w") as f:
        f.write("body,cycle_time,radius\n")
        for row in rows:
            f.write(",".join(map(str, row)) + "\n")


def main():
    rng = np.random.default_rng(SEED)
    train = make(rng, 8, c=3.7, r_lo=0.4, r_hi=30.0, prefix="A")
    hold = make(rng, 5, c=0.85, r_lo=1.0, r_hi=12.0, prefix="B")
    write(HERE / "data/synthetic_train.csv", train)
    write(HERE / "hidden/synthetic_holdout.csv", hold)
    (HERE / "hidden/synthetic_truth.yaml").write_text(yaml.safe_dump({
        "law": "T = C*r**(5/4)", "exponent": EXPONENT, "C_train": 3.7, "C_holdout": 0.85,
        "noise_lognormal_sigma": NOISE, "seed": SEED,
    }))


if __name__ == "__main__":
    main()
