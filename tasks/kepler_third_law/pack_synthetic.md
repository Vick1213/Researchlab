# Knowledge pack: system A

Eight small bodies circle a single massive central body in a closed system. Each
body follows a nearly circular path at a fixed radius `r` and returns to its
starting position after a cycle time `T`. Radius is measured in spans, time in
ticks; these units are local to this system.

Observers have established that each body's motion is stable and periodic, and
that farther bodies take longer. Nothing else is known about the forces involved.

## Data

The table `synthetic_train.csv` (below) gives each body's cycle time and radius.
Measurements carry small random errors (well under 1%).

## Your task

Find a single quantitative law relating cycle time `T` to radius `r` that holds for
all eight bodies. It should be a law of nature, not a curve fit: it should carry
over to other systems of this kind, with at most a change of constant.
