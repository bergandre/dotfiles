#!/usr/bin/env python
# Build waybar-icons.otf: brand logos Nerd Fonts lacks, as private-use glyphs.
# wow.svg = cbi:wow from Custom Brand Icons (CC BY-NC-SA 4.0, github.com/elax46/custom-brand-icons)
# Rebuild: python fonts/build.py   (needs python-fonttools)
import os
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import SVGPath

HERE = os.path.dirname(os.path.abspath(__file__))
UPM, VIEW, PAD = 1000, 24, 3.5  # svgs use a 24x24 viewBox; crop the empty margin so the logo fills the em
GLYPHS = {"wow": 0x10FF00}

fb = FontBuilder(UPM, isTTF=False)
fb.setupGlyphOrder([".notdef", *GLYPHS])
fb.setupCharacterMap({cp: name for name, cp in GLYPHS.items()})
charstrings = {".notdef": T2CharStringPen(UPM, None).getCharString()}
for name in GLYPHS:
    pen = T2CharStringPen(UPM, None)
    s = UPM / (VIEW - 2 * PAD)
    # svg y points down, font y points up; baseline a bit below the icon
    SVGPath(os.path.join(HERE, f"{name}.svg")).draw(TransformPen(pen, (s, 0, 0, -s, -PAD * s, UPM * 0.85 + PAD * s)))
    charstrings[name] = pen.getCharString()
fb.setupCFF("WaybarIcons-Regular", {"FullName": "Waybar Icons"}, charstrings, {})
fb.setupHorizontalMetrics({".notdef": (UPM, 0), **{n: (UPM, 0) for n in GLYPHS}})
fb.setupHorizontalHeader(ascent=850, descent=-150)
fb.setupNameTable({"familyName": "Waybar Icons", "styleName": "Regular"})
fb.setupOS2(sTypoAscender=850, sTypoDescender=-150, usWinAscent=850, usWinDescent=150)
fb.setupPost()
fb.save(os.path.join(HERE, "waybar-icons.otf"))
