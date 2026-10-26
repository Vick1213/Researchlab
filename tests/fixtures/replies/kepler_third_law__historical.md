Here is how I arrived at the law.

I compared how fast the periods grow with how fast the distances grow. Going from Mercury to Saturn, the distance rises by a factor of about 24.6 and the period rises by a factor of about 122. The period therefore grows faster than the distance but more slowly than the distance squared. This fits the observation that outer planets have farther to travel and also move more slowly.

On logarithmic scales, ln T plotted against ln a gives a straight line:
- Mercury to Saturn: ln(10759/87.97) / ln(9.537/0.387) = 4.806 / 3.205 ≈ 1.50.
- Earth to Jupiter: ln(11.862) / ln(5.203) = 2.473 / 1.649 ≈ 1.50.

The slope is 3/2, so T² is proportional to a³. Checking T²/a³ for each planet, with T in days and a in Earth–Sun distances:
- Mercury: 7739 / 0.05796 ≈ 1.335×10⁵
- Venus: 50490 / 0.3779 ≈ 1.336×10⁵
- Earth: 133415 / 1 = 1.334×10⁵
- Mars: 471942 / 3.540 ≈ 1.333×10⁵
- Jupiter: 1.8771×10⁷ / 140.85 ≈ 1.333×10⁵
- Saturn: 1.1576×10⁸ / 867.4 ≈ 1.335×10⁵

All six planets give the same value to within about 0.1%. That is much closer than the few-percent agreement of the nested-solids model, and it needs only one constant. The exponents 2 and 3 are exact whole numbers, so I wrote them as numbers rather than fitting them.

The law should carry over to other systems with only a new constant. Jupiter's four moons are the test case: their periods and distances should also give a constant T²/a³, but with a different value from the Sun's. The constant belongs to the central body.

```json
{
  "law": "T**2 = k*a**3",
  "parameters": {
    "k": {
      "units": "time**2/length**3",
      "system_dependent": true,
      "initial": 133400
    }
  },
  "explanation": "For every planet, the square of the period divided by the cube of the mean distance is the same number, to about 0.1%. On log scales, period against distance is a straight line with slope exactly 3/2. The constant k belongs to the central body: Jupiter's moons should follow the same T^2 = k a^3 rule with a different k (the initial value assumes T in days and a in Earth-Sun distances)."
}
```
