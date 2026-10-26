# Knowledge pack: the planetary system, spring 1618

You are working with the astronomical knowledge available in Europe in early 1618.

## What is accepted (by the Copernican school)

- The Sun is at the centre. Six planets orbit it, in order: Mercury, Venus, Earth,
  Mars, Jupiter, Saturn.
- Each planet moves on an ellipse with the Sun at one focus, and the line from the
  Sun to the planet sweeps out equal areas in equal times (established from Tycho
  Brahe's observations of Mars, published 1609).
- The relative sizes of the orbits are known from geometry, with the Earth-Sun
  mean distance as the unit. The sidereal periods are known from long-run
  observation.
- Planets farther from the Sun take longer to go around. They also appear to move
  more slowly along their paths, not just farther.
- Four moons circle Jupiter (discovered 1610). Their periods and distances from
  Jupiter have been measured.

## What is not known

No rule is known that connects the size of a planet's orbit to its period. A
nested-solids model of the orbit sizes (1596) matches the distances only to a few
percent and says nothing about periods. Musical and simple-ratio relations between
distances and speeds have been tried without success.

## Data

The table `planets.csv` (below) gives each planet's sidereal period in days and its
mean distance from the Sun in units of the Earth-Sun mean distance.

## Your task

Find a single quantitative law relating a planet's period `T` to its mean distance
`a` that holds for all six planets. It should be a law of nature, not a curve fit:
it should carry over to other systems of bodies orbiting a common centre, with at
most a change of constant.
