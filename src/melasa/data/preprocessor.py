import re

def preprocess(md: str) -> str:

# columns: <!-- c -->, <!-- | -->, <!-- c. -->
# variants: c21, c12, c31, c111 (ratios), optional t/b suffix for top/bottom alignment (ct, cb, c21t, ...)
    def cols_open(m):
        ratio, align = m.group(1), m.group(2)
        classes = "cols" + (f" cols{ratio}" if ratio else "")
        if align:
            classes += " cols-top-align" if align == "t" else " cols-bottom-align"
        return f'\n<div class="{classes}" markdown="1"><div markdown="1">\n'

    md = re.sub(r"<!--\s*c(21|12|31|111)?([tb])?\s*-->", cols_open, md)
    md = re.sub(r"<!--\s*\|\s*-->", r'\n</div><div markdown="1">\n', md)
    md = re.sub(r"<!--\s*c\.\s*-->", r'\n</div></div>\n', md)

# single close: </div> (for boxes, footnotes, etc.)
    md = re.sub(r"<!--\s*\.\s*-->", r'\n</div>\n', md)

# width: <!-- w100% -->, <!-- w50% -->
    md = re.sub(r"<!--\s*w([0-9]+)%\s*-->", r'<!-- .element style="width:\1%" -->', md)
    md = re.sub(r"<!--\s*w([0-9]+)\s*-->", r'<!-- .element style="width:\1%" -->', md)

# absolute position with width: <!-- absolute 100 200 10 -->
    md = re.sub(r"<!--\s*absolute ([0-9.]+) ([0-9.]+) ([0-9.]+)\s*-->", r'<!-- .element style="position: absolute; transform: translate(-50%, -50%); top:\1%; left:\2%; width:\3%" -->', md)

# vertical space: <!-- vspace2.5 -->
    md = re.sub(r"<!--\s*vspace([0-9.]+)\s*-->", r'\n<p style="margin-top: \1em;"></p>\n', md)

# left/right float <!-- float-left -->, <!-- float-right -->
    md = re.sub(r"<!--\s*float-left\s*-->", r'<!-- .element style="float: left" -->', md)
    md = re.sub(r"<!--\s*float-right\s*-->", r'<!-- .element style="float: right" -->', md)

# box: <!-- box -->, <!-- . -->
    md = re.sub(r"<!--\s*box\s*-->", r'\n<div class="box" markdown="1">\n\n', md)

# footnote: <!-- footnote -->, <!-- . -->
    md = re.sub(r"<!--\s*footnote\s*-->", r'\n<div class="footnote" markdown="1">\n\n', md)

# math: <!-- e -->, <!-- e. -->
    md = re.sub(r"<!--\s*e\s*-->", r'\n<div markdown="1">\\[\\begin{aligned}', md)
    md = re.sub(r"<!--\s*e\.\s*-->", r'\\end{aligned}\\]</div>', md)

# fragments: <!-- f0 -->, <!-- f1 -->
    md = re.sub(r"<!--\s*f([0-9]+)\s*-->", r'<!-- .element: class="fragment" data-fragment-index="\1" -->', md)

# fit-text: <!-- fit -->
    md = re.sub(r"<!--\s*fit\s*-->", r'<!-- .element class="r-fit-text" -->', md)

# auto-animate: <!-- anim0 -->, <!-- anim -->
    md = re.sub(r"<!--\s*anim\s*-->", r'<!-- .element data-auto-animate -->', md)
    md = re.sub(r"<!--\s*anim0\s*-->", r'<!-- .element data-auto-animate data-auto-animate-restart -->', md)

# left/right text-align: <!-- text-left -->, <!-- text-right -->
    md = re.sub(r"<!--\s*text-left\s*-->", r'<!-- .element style="text-align: left" -->', md)
    md = re.sub(r"<!--\s*text-right\s*-->", r'<!-- .element style="text-align: right" -->', md)



    return md

