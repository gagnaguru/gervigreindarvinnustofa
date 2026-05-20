# RacingGame — Prompt saga

## Módel

Composer 2.5 — ekki skráð í spjallsögu. Búið til í Cursor IDE.

## Spjall-ID

`ac9dcb19-a912-48c8-801c-87bdad1fdb5c` (í analytics-gervigreind workspace)

## Fyrirspurnir

### 1. Upphaflega fyrirspurnin

> Create a single player browser based racing game

### 2. Villuleiðrétting

> the finish line is not correctly placed. It is paralell to track and not near the start

## Samantekt

Leikurinn — "Circuit Sprint" — var búinn til í tveimur skrefum:

1. Notandinn bað um einfaldan eins manns kappakstursleik í vafra. Agentinn bjó til `RacingGame/index.html` með hringbraut séð ofan frá, 3 hringjum, tímamælingu og niðurtalningu.
2. Notandinn benti á að marklínan var röng — hún var samsíða brautinni og ekki nálægt byrjunarstað. Agentinn lagaði þetta með því að setja lóðrétt mótaðri marklínu á neðstu beinu (hornrétt á akstursstefnu) og uppfærði hringteljara og árekstrargreiningu.

Lokaútgáfan er ein `index.html` skrá með WASD/örvastýringum og "haltu þig á brautinni" eðlisfræði.
