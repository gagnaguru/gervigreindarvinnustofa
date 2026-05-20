# FightingGame — Prompt saga

## Módel

Óþekkt — ekki skráð í spjallsögu. Búið til í Cursor IDE.

## Spjall-ID

`61f8e8c1-d5f0-4463-82ad-20b63e9c29f1` (í analytics-gervigreind workspace)

## Fyrirspurnir

### 1. Upphaflega fyrirspurnin (eina fyrirspurnin)

> Create a fighting game. Where I can choose between 9 different fighters of different races, skills and with different abilities.
> We can then fight player vs. player (2 player game) or player vs. computer (1 player game).
>
> The characters are controlled using different sides of the keyboard and have their own combos that unlock their special attacks or moves.

## Samantekt

Leikurinn — "Clash of Realms" — var búinn til í einu spjalli með einni fyrirspurn. Agentinn skoðaði `RacingGame/index.html` til viðmiðunar um stíl og bjó síðan til `FightingGame/index.html` sem eina stóra HTML-skrá (~2.068 línur) með öllu innbyggðu.

Niðurstaðan inniheldur:
- 9 bardagapersónur (Human Knight, Ninja, Orc, Elf Archer, Fire Mage, Ice Witch, Robot, Demon, Werewolf) með mismunandi eiginleika og 4 sérhæfileika hver
- 1P (gegn tölvu) eða 2P (staðbundið) leikham
- Stýringar: Spilari 1 með WASD + F/G/H, Spilari 2 með örvum + J/K/L
- Persónuval, best-of-3 lotur, HUD og gervigreind andstæðingur
