# FT81x Utils

Tools for working with Bridgetek's FT81x chips.

## Font generator

Converts OTF fonts to bytes for loading into `RAM_G` on the chip.

1. Set up environment if not done yet: `pipenv shell`.
2. Drop `font.otf` in the directory.
3. Run `python3 generate-font.py`
4. By default, the script generates preview of glyphs in `out.png` and outputs data to `progmem.hpp`.