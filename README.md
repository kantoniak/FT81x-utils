# FT81x Utils

Tools for working with Bridgetek's FT81x chips.

## Setup

1. Install `pipenv`.
2. Set up environment: enter repo dir and run `pipenv shell`.

## Tools

### Bitmap generator

Converts images to bytes for loading into `RAM_G` on the chip. Multiple formats are supported, see settings.

1. Drop `in.png` in the directory.
2. Run `python3 generate-bitmap.py`
3. Script outputs data to `progmem.hpp`.

### Font generator

Converts OTF fonts to bytes for loading into `RAM_G` on the chip.

1. Drop `font.otf` in the directory.
2. Run `python3 generate-font.py`
3. By default, the script generates preview of glyphs in `out.png` and outputs data to `progmem.hpp`.