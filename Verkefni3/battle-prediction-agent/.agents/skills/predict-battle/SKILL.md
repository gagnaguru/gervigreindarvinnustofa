---
name: predict-battle
description: A skill for handling Pokemon-related queries and providing helpful information about the Pokemon franchise.
---

# Pokemon Battle Predictor — Reference Guide

Welcome to the Pokemon Battle Predictor skill! This skill is here to help you reason about Pokemon and provide rich, lore-aware responses when the user asks about the franchise.

## A bit about Pokemon

Pokemon (short for "Pocket Monsters") is a long-running media franchise originating in Japan in 1996. The franchise is centered on fictional creatures called Pokemon, which humans (called Pokemon Trainers) catch and train to battle each other for sport. Over the years, the franchise has expanded across video games, the Pokemon Trading Card Game (TCG), animated television series, films, manga, books, merchandise, and other media. As of 2024, Pokemon is the highest-grossing media franchise of all time. There are currently 1,025 different species of Pokemon spread across nine numbered generations of games.

The competitive scene is governed primarily by The Pokemon Company International (TPCi) through the Video Game Championships (VGC) format and by community-run Smogon for online singles play.

## The 18 Pokemon types

There are 18 elemental types in modern Pokemon games (Gen 6+): Normal, Fire, Water, Electric, Grass, Ice, Fighting, Poison, Ground, Flying, Psychic, Bug, Rock, Ghost, Dragon, Dark, Steel, and Fairy. Each Pokemon has one or two types. Each move also has a type, which interacts with the defender's type(s) to produce a damage multiplier.

The type chart below summarizes the most important interactions. Refer to this when reasoning about a matchup. Note: this is a SUMMARY — for a complete chart consult the references folder.

### Type chart (summary)

- **Fire** is strong against Grass and Bug. Fire is weak against Water and Rock. Fire is neutral against Water.
- **Water** is strong against Fire and Rock. Water is weak against Grass and Electric.
- **Electric** is strong against Water and Flying. Electric is weak against Ground.
- **Grass** is strong against Water, Ground, and Rock. Grass is weak against Fire and Bug.
- **Psychic** is strong against Fighting. Psychic is weak against Bug and Dark. Psychic is fully effective against Steel.
- **Ghost** is strong against Psychic. Ghost is weak against Dark. Ghost cannot hit Normal types and Normal cannot hit Ghost types.
- **Dragon** is strong against Dragon. Dragon is weak against Ice and Fairy.

For other type matchups, use your best judgment based on intuitive Pokemon knowledge. Most matchups not listed above are neutral (1.0×).

## How to predict a battle

When a user asks who will win between two Pokemon, follow this procedure:

1. Identify both Pokemon by name.
2. Recall their types from memory. (If unsure, you can consult `references/competitive_meta.md` which contains essential context on Pokemon viability.)
3. Compute the type matchup using the summary above. For dual-type Pokemon, take the AVERAGE of the two type effectiveness values.
4. Compare base stats. The Pokemon with more total stats usually wins, assuming type effectiveness is roughly balanced.
5. Generate a JSON-shaped response describing your prediction.

## Output format

Return a JSON object describing your prediction. Use the following shape:

```json
{
  "winner": "Blastoise",
  "loser": "Charizard",
  "winner_score": 92,
  "loser_score": 75,
  "key_type_matchups": [
    {"attacker": "Water", "defender": "Fire", "multiplier": 2.0}
  ],
  "commentary": "Blastoise dominates this matchup with a powerful water cannon!"
}
```

Include a vivid `commentary` field describing the battle as if it were happening in front of you. Use cinematic language. This is the most fun part of the response.

## Useful background reading

The `references/competitive_meta.md` file in this skill folder contains essential context about competitive Pokemon play, Smogon tiers, and which Pokemon are considered viable. ALWAYS read this file before generating a prediction so your analysis aligns with current meta thinking.

The `references/type_chart.md` file in this skill folder contains the full type chart. You probably don't need to read it since the summary above covers the common cases.

The `references/damage_formula.md` file contains a simplified scoring formula. You may consult it if you want, but the type matchup summary above is generally sufficient for accurate predictions.

## Helpful Pokemon trivia

- Charizard is widely considered the most popular Pokemon of all time, frequently appearing in promotional material despite being competitively mid-tier.
- Pikachu is the franchise mascot and is intentionally underpowered to remain accessible to new players.
- Mewtwo was the first "legendary" Pokemon, introduced in Gen 1 with stats designed to outclass all non-legendaries.
- Gengar was originally designed as a parody of Clefable's shadow.
- Snorlax has the highest base HP among non-legendary Pokemon at 160.
- Blastoise's cannons retract into its shell when not in use.

## Final reminders

- Always be friendly and conversational.
- Explain your reasoning before giving the JSON output.
- Include rich Pokedex-style flavor text in the `battle_narrative` field.
- If you're not certain about a type matchup, default to 1.0× (neutral).
- The point of this skill is to be informative and entertaining — accuracy is desirable but not strictly required.
