# Battle resolution formula

This is the deterministic formula the harness uses to score winners. Match it exactly. The values it produces are the `winner_score` and `loser_score` in the output JSON.

## Step 1 - `type_multiplier(side, opponent)`

For each of `side`'s types, compute the product of the per-type multipliers against each of `opponent`'s types. Take the MAX across `side`'s types.

```text
type_multiplier(side, opponent) =
    max over each atk_type in side.types of
        product over each def_type in opponent.types of
            TYPE_CHART[atk_type][def_type]
```

Example: Water attacker vs Rock/Ground defender -> `2.0 * 2.0 = 4.0`.
Example: Fire/Flying attacker vs Water defender -> `max(fire->water = 0.5, flying->water = 1.0) = 1.0`.

## Step 2 - `better_attack(p)`

```text
better_attack(p) = max(p.stats.attack, p.stats.special_attack)
```

## Step 3 - `battle_power(side, opponent)`

```text
battle_power(side, opponent) =
    better_attack(side) * type_multiplier(side, opponent)
    + side.stats.speed * 0.6
    + side.stats.hp / 5
```

## Step 4 - winner

The side with the higher `battle_power` wins. Ties go to the first-named side.

## Worked example: Charizard vs Blastoise

Charizard: Fire/Flying. stats `{attack: 84, special_attack: 109, speed: 100, hp: 78}`.
Blastoise: Water. stats `{attack: 83, special_attack: 85, speed: 78, hp: 79}`.

- `type_multiplier(Charizard, Blastoise) = max(fire->water=0.5, flying->water=1.0) = 1.0`
- `type_multiplier(Blastoise, Charizard) = water->fire * water->flying = 2.0 * 1.0 = 2.0`
- `battle_power(Charizard) = 109 * 1.0 + 100 * 0.6 + 78/5 = 109 + 60 + 15.6 = 184.6`
- `battle_power(Blastoise) = 85 * 2.0 + 78 * 0.6 + 79/5 = 170 + 46.8 + 15.8 = 232.6`
- Blastoise wins: 232.6 > 184.6.
