#!/usr/bin/env python3
"""Build a plain HTML slide deck.

    build.py BODY OUT --title "Deck name"   build from a slide body
    build.py DECK OUT                       rebuild an existing deck on the current shell

BODY holds the <section class="slide"> elements, optionally preceded by one
<style> block for deck-specific CSS, which is where a palette override goes.
A deck built here keeps its body between the deck:body markers, so it can be
rebuilt later to pick up fixes to the shell.

Exits 1 if the output has dashes, unfilled placeholders or no slides.
"""
import argparse
import html
import pathlib
import re
import sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
START = "<!-- deck:body:start -->"
END = "<!-- deck:body:end -->"
DASHES = (chr(0x2014), chr(0x2013), "&mdash;", "&ndash;")  # em dash, en dash


def main():
    p = argparse.ArgumentParser(description="Build a plain HTML slide deck.")
    p.add_argument("source", help="slide body, or an existing deck to rebuild")
    p.add_argument("out", help="output .html path")
    p.add_argument("--title", help="deck name; read from an existing deck if omitted")
    a = p.parse_args()

    src = pathlib.Path(a.source).read_text(encoding="utf-8")
    title = a.title
    if START in src:
        body = src.split(START, 1)[1].split(END, 1)[0].strip("\n")
        if title is None:
            m = re.search(r"<title>(.*?)</title>", src, re.S)
            title = html.unescape(m.group(1)) if m else None
    else:
        body = src.strip("\n")
    if not title:
        sys.exit("build.py: --title is required when building from a body")

    shell = (SKILL / "assets" / "deck-shell.html").read_text(encoding="utf-8")

    out = (
        shell.replace("{{TITLE}}", html.escape(title, quote=False))
        .replace("{{BODY}}", body)
    )
    pathlib.Path(a.out).write_text(out, encoding="utf-8")

    slides = out.count('<section class="slide')
    dashes = {d: out.count(d) for d in DASHES if d in out}
    leftover = sorted(set(re.findall(r"\{\{[A-Z]+\}\}", out)))
    print("wrote %s: %d slides, %d KB" % (a.out, slides, len(out) // 1024))
    if dashes:
        print("dashes found: %s" % dashes)
    if leftover:
        print("unfilled placeholders: %s" % ", ".join(leftover))
    if not slides:
        print('no <section class="slide"> found')
    sys.exit(1 if (dashes or leftover or not slides) else 0)


if __name__ == "__main__":
    main()
