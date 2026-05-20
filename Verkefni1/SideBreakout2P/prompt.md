# SideBreakout2P — Prompt saga

## Módel

Codex 5.3. Búið til í Cursor IDE.

## Spjall-ID

`1eacfc6e-6c5a-4c2a-a752-dcf44d47c593` (í analytics-gervigreind workspace)

## Fyrirspurnir

### 1. Upphaflega fyrirspurnin

> Create a 2 player breakout game - browser based. It should be rotated 90 degrees from the original so the ball goes from side to side and the players need to "defend" their side.
> Here is an example of a 2-player breakout game.
> https://github.com/Couchfriends/breakout

### 2. Leiðrétting

> Create a seperate directory for the game, don't destroy the PhoneInvaders game

### 3. Viðbætur og stílhönnun

> Create an opening screen that includes the controls.
> Make it possible to select 2 balls version (a ball starts on each side).
> Implement the breakout using .js and add a css style file.
> Make the style in the colors of http://www.nova.is website and the NOVA brand.
> Add the Nova stærsti skemmtistaður í heimi in the background, (keep it faint/transparent)

## Samantekt

Leikurinn var búinn til í þremur skrefum:

1. Notandinn bað um 2ja manna breakout-leik snúinn um 90° þar sem bolti fer til hliðar og spilarar verja sína hlið. Tilvísun í Couchfriends breakout á GitHub.
2. Agentinn byrjaði á að nota PhoneInvaders möppuna en notandinn bað um sérstaka möppu.
3. Notandinn bað um upphafsskjá með stýringum, 2ja bolta valkost, aðskildar JS/CSS skrár, NOVA litasamsetningu (fjólublátt/bleikt) og fölskan slagorðstexta í bakgrunni.

Lokaútgáfan inniheldur `index.html`, `styles.css` og `game.js`.
