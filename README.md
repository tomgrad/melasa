# melasa
Wrapper for [MkSlides](https://github.com/MartenBE/mkslides) that adds preprocessor tags (columns, boxes, ...) with a small structural theme, and a library of styles for new decks.


## Features
- Two-column layout with different alignments and ratios
- Custom width for elements
- Box elements
- Math support
- Fragmented elements
- Auto-animate support

## Install

`uv tool install .` (or `uv tool install -e .` while developing)

## Usage

```
melasa init [--style NAME]  # create index.md, style.css and mkslides.yml
melasa init --list          # list available styles
melasa serve [PATH]      # live preview, PATH defaults to .
melasa build [PATH]      # writes site-<dirname> in the current directory
melasa build PATH -d out --optimize --max-size 1920 --quality 82
melasa optimize SITE_DIR # optimize an already built site
```

The shared `preprocessor.py`, `melasa.css` (structural CSS for the tags) and base `mkslides.yml` ship with the package, nothing is copied into the slides directory. A deck's `mkslides.yml` is merged over the defaults.

The reveal.js theme is selected by name in `mkslides.yml`:

```yaml
slides:
    theme: league   # beige, black, league, sky, ... or a URL
```

CSS is applied in this order, so later layers override earlier ones:

1. the reveal.js theme from `slides.theme`
2. the shared `melasa.css` (layout for the custom tags only)
3. an optional `style.css` in the deck root: your overrides, loaded last

## Styles

`melasa init --style NAME` copies a style from the library into the deck: its `style.css` (overrides only, no theme import) and a `mkslides.yml` naming the reveal.js theme. The library lives in `src/melasa/data/styles/<name>/`; to add a style, create a directory there with those two files.

`--optimize` is off by default. It only touches the built site: images larger than `--max-size` are scaled down, PNG/JPEG are converted to WebP (kept only when smaller), and references in the site are updated. Sources are never modified.


## Custom elements

- two-column layout

```
<!-- c -->
left
<!-- | -->
right
<!-- c. -->
```

- two columns with top alignment

```
<!-- ct -->
...
```

- two columns with bottom alignment

```
<!-- cb -->
...
```

- two columns with 2:1 ratio

```
<!-- c21 -->
...
```

- two columns with 1:2 ratio

```
<!-- c12 -->
...
```

- two columns with 3:1 ratio

```
<!-- c31 -->
...
```

- three columns

```
<!-- c111 -->
...
```

- elements with width

```
![image](image.png)<!-- w100% -->
![image](image.png)<!-- w50% -->
![image](image.png)<!-- w25% -->
```

- box

```
<!-- box -->
text
<!-- . -->

<!-- box --><!-- w50% -->
...
```

- footnote and text-align

```
<!-- footnote -->
text
<!-- . -->

<!-- footnote --><!-- text-left -->
...


<!-- footnote --><!-- text-right -->
...
```

- float

```
![](image.img)<!-- float-left -->

![](image.img)<!-- float-right -->
```

- vertical space

```
<!-- vspace1.5 -->

<!-- vspace3 -->
```

- math

```
<!-- e -->
\nabla \cdot \vec{E} &= \frac{\rho}{\varepsilon_0} \\
\nabla \cdot \vec{B} &= 0
<!-- e. -->
```

- fragments

```
- item 1 <!-- f0 -->
- item 2 <!-- f1 -->
```

- absolute position (top and left of the middlepoint, width)

```
![](image.png)<!-- absolute 25 25 25 -->

![](image.png)<!-- absolute 50 50 25 --><!-- f0 -->

![](image.png)<!-- absolute 75 75 25 --><!-- f1 -->

```


- fit
  
```
# Title <!-- fit -->
```

- auto-animate

```
<!-- anim0 -->
## Title <!-- fit -->
----
<!-- anim -->
## Title 
content
```
