# nyx iteration log

| step | change | similarity |
|---|---|---|
| 0 | skeleton, unchanged (Juno's palette and rules) | 0.4084 |
| 1 | Nyx palette refit (skin, platinum hair, mask, indigo coat, tee, olive pants, boots, chrome shin, lime), parts with leg_l chrome, no rules; eight grids drafted+cleaned+applied | 0.8402 |
| 2 | open coat front (tee/belt/pants stripes), lime sleeve band, back collar, coat hem over the legs from behind, knee seam; chrome and pants shade refit; neck skin | 0.8687 |
| 3 | grids re-drafted without the speckle pass (last-row clean only): the platinum hair's grey strands kept | 0.8767 |
| 4 | grows: far shoulder in both 3/4 fronts (n=3), far sleeve in down_side_l, collar/shoulders front+back, far boot toe row in 3/4 | 0.8813 |
| 5 | sleeve band: front/side on both arms, back 3/4 on one sleeve, none from behind; lime back emblem (2 px) | 0.8841 |
| 6 | per-facing: coat collar over the neck (side, back), sleeves over the hands in side/3-4 views (hands in pockets), lime hem row side_l/up, boots one row up in side_l/down_side_l | 0.8879 |
| 7 | 3/4 shoulder grow moved after the opening stripes (tee/belt/pants now one column strip); back emblem straight | 0.8887 |
| 8 | harvested per-facing trim: profile collar+front piping, sleeve end dark in 3/4 back, band higher in side_l, chrome foot column (up, up_side, down), shin highlight 3/4 front, lime laces | 0.8930 |
| 9 | legend gains coat chars c/C (collar in the head's bottom rows); grids re-drafted raw (up keeps the last-row clean); outline keep = every legend char; no doubled hem row from behind | 0.8947 |
| 10 | legend extended with every palette slot seen on/beside the head (skin light/blush, coat light, tee, lime trim, lens light); grids re-drafted raw (up kept) | 0.8966 |
| 11 | shrink: sleeves+hands a column narrower from behind (up both sides, up_side left, up_side_l right) via outline region + edge-touching-none clear | 0.8999 |
| 12 | harvest: profile coat back edge shrunk, hands' left edge shrunk (3 views), sleeve band off in down_side, front piping off in side, coat skirt + far hand grown in down_side_l (legs shrink in side rejected: it erased the cyber-shin) | 0.9025 |
| 13 | side grid re-drafted after the shrinks; optimizer: coat ink lighter (#252320: fold lines, not outline), tee shade darker (#323130: in the coat's shadow) | 0.9043 |
| 14 | sweep picks with a reading: lime cuffs at the sleeve end in both profiles, grey soles from 3/4 back left, lime skirt piping over the far leg in down_side_l, shoulder seam in front | 0.9074 |
| 15 | shoulder/collar grows removed from front and back: grow's fill-behind left unoutlined pixels at the shoulder corners (visible from behind as indigo outside the outline) | 0.9072 |
| 16 | re-based on the fixed generator (grow corners, shrink rule): shrinks as shrink rules, profile coat-back shrink dropped (black column), collar grow back in front and behind; sweep 2 picks: profile coat back fold, trouser over boot 3/4 back left, dark sleeve opening down_side_l, sleeve fold side_l | 0.9081 |
| 17 | re-scored under the shrink fix (whole new silhouette outlined: from behind the hands become dark sleeve ends); unused legend chars o, l removed | 0.9075 |

Metric and generator changes during the run (scores before and after are not directly comparable):
- step 2: similarity uses a zero-filled shift instead of np.roll (the sole row no longer wraps to row 0).
- step 7: straight stripes take their median column over all the part's rows (no score change for this recipe).
- step 16: grow keeps a vacated corner as outline; `shrink` rule type (step 15's 0.9072 re-scored 0.9067).
- step 17: shrink inks the whole new silhouette (step 16's 0.9081 re-scored 0.9075).
