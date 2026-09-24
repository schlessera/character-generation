# replica iteration log

Each step: `just compare replica` (mockup above the render), read the text view, change the recipe
(or the generator), re-render, look again. `step-NN.toml` is the recipe after step NN, saved every
five steps. Similarity: mean over the five mockup views. Palette ceiling (`--ceiling`): 0.9__.

| step | change | similarity |
|---|---|---|
| 0 | skeleton recipe, placeholder colours | |
