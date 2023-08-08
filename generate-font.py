import math
from typing import Iterable, Tuple
from utils import *

from PIL import Image, ImageDraw, ImageFont


def get_width_padded_to_bytes(width: int, bit_depth: int) -> int:
  return math.ceil(width * bit_depth / 8) * 8 // bit_depth


def render_glyph(
    glyph: str,
    font: ImageFont.FreeTypeFont,
    image_height: int,
    image_crop_top: int,
    padded_image_width: int,
    rendering_scale: int,
    canvas_width: int,
    canvas_height: int,
    font_x_adjust: float,
    font_y_adjust: float) -> Image.Image:
  padded_canvas_width = rendering_scale*padded_image_width
  image = Image.new('L', size=(padded_canvas_width, canvas_height))
  draw = ImageDraw.Draw(image)
  _, _, w, h = draw.textbbox((rendering_scale*font_x_adjust, rendering_scale*font_y_adjust), glyph, font, align="center")
  text_pos = ((canvas_width-w)/2, (canvas_height-h)/2)
  draw.text(text_pos, glyph, fill="#FFF", font=font, align="center")
  return image \
    .resize((padded_image_width, image_height), resample=Image.Resampling.BICUBIC) \
    .crop((0, image_crop_top, padded_image_width, image_height))


def render_bitmap(
    font: ImageFont.FreeTypeFont,
    ascii_codes: Iterable[int],
    glyph_image_height: int,
    image_crop_top: int,
    padded_image_width: int,
    bit_depth: int,
    rendering_scale: int,
    canvas_width: int,
    canvas_height: int,
    glyph_height: int,
    font_x_adjust: float,
    font_y_adjust: float) -> Tuple[Image.Image, Iterable[int], int]:
  bitmap_bytes = list()
  bitmap_byte_count = 0

  ascii_to_render = set(ascii_codes)
  first_char_code = min(ascii_to_render)
  last_char_code = max(ascii_to_render)
  image_height = (last_char_code - first_char_code + 1) * glyph_height
  preview_image = Image.new('L', size=(padded_image_width, image_height))

  pixels_per_glyph = padded_image_width * glyph_image_height
  (empty_glyph_bytes, empty_glyph_byte_count) = join_to_bytes([0]*pixels_per_glyph, bit_depth)

  for ascii_code in range(first_char_code, last_char_code+1):
    if ascii_code not in ascii_to_render:
      bitmap_bytes.extend(empty_glyph_bytes)
      bitmap_byte_count += empty_glyph_byte_count
      continue

    glyph = chr(ascii_code)
    glyph_pos = ascii_code - first_char_code

    # Build glyph
    image = render_glyph(
      glyph,
      font,
      glyph_image_height,
      image_crop_top,
      padded_image_width,
      rendering_scale,
      canvas_width,
      canvas_height,
      font_x_adjust,
      font_y_adjust)
    preview_image.paste(image, (0, glyph_height*glyph_pos))

    # Get output bytes
    glyph_data = change_bit_depth(image.getdata(), bit_depth)
    (glyph_bytes, glyph_byte_count) = join_to_bytes(glyph_data, bit_depth)
    bitmap_bytes.extend(glyph_bytes)
    bitmap_byte_count += glyph_byte_count

  return (preview_image, bitmap_bytes, bitmap_byte_count)


# Settings

def run():
  image_width = 10 # This width will be padded based on bit depth, see 4.7.linestride in docs
  image_height = 18
  image_crop_top = 1
  font_size = 17
  font_file = "font.otf"
  glyphs_to_render = None # "012345689"
  image_file = None # "font.png" # Input image
  font_x_adjust = 0.25
  font_y_adjust = 4
  rendering_scale = 4
  preview_filename = 'out.png' # None
  preview_only = False
  bit_depth = 4
  indent_spaces = 2
  bitmap_byte_columns = 10
  output_filename = 'progmem.hpp'

  padded_image_width = get_width_padded_to_bytes(image_width, bit_depth)
  canvas_width = rendering_scale * image_width
  canvas_height = rendering_scale * image_height

  glyph_width = image_width
  glyph_height = image_height - image_crop_top

  ascii_codes = list(range(ord(' '), 128))
  if font_file and glyphs_to_render:
    ascii_codes = list(map(ord, ''.join(sorted((dict.fromkeys(glyphs_to_render))))))

  # End of settings


  # Build bitmap
  if font_file:
    font = ImageFont.truetype(font_file, rendering_scale*font_size, encoding="unic")
    (preview_image, bitmap_bytes, bitmap_byte_count) = render_bitmap(
      font,
      ascii_codes,
      image_height,
      image_crop_top,
      padded_image_width,
      bit_depth,
      rendering_scale,
      canvas_width,
      canvas_height,
      glyph_height,
      font_x_adjust,
      font_y_adjust)
  elif image_file:
    preview_image = Image.open(image_file)
    bitmap_data = change_bit_depth(preview_image.getdata(), bit_depth)
    (bitmap_bytes, bitmap_byte_count) = join_to_bytes(bitmap_data, bit_depth)
  else:
    raise ValueError('Either font or image required.')


  if preview_filename:
    preview_image.save(preview_filename)
    if preview_only:
      exit()

  # Built font metrics
  metrics_width_bytes = list()
  for ascii_code in range(0, 128):
    char_width = image_width if ascii_code in ascii_codes else 0
    metrics_width_bytes.append(char_width)
  bitmap_layout_id = bit_depth_to_l_layout(bit_depth)
  bitmap_linestride = padded_image_width * bit_depth // 8


  with open(output_filename, "w") as out_file:
    render_uint32 = lambda val: render_byte_list(list(val.to_bytes(4, 'little')), 8, indent_spaces)
    out_file.write(f"const uint32_t FONT_BITMAP_BYTE_COUNT = {bitmap_byte_count};\n")
    out_file.write("const uint8_t FONT_BITMAP_BYTES[] PROGMEM = {\n")
    out_file.write(render_byte_list(bitmap_bytes, bitmap_byte_columns, indent_spaces))
    out_file.write("\n")
    out_file.write("};\n\n")
    out_file.write("// Write metrics in RAM at address aligned to 4 bytes.\n")
    out_file.write("const uint8_t FONT_METRICS[] PROGMEM = {\n")
    out_file.write(" "*indent_spaces)
    out_file.write("// Character widths\n")
    out_file.write(render_byte_list(metrics_width_bytes, 8, indent_spaces))
    out_file.write("\n")
    out_file.write(" "*indent_spaces)
    out_file.write("// Values below are in Little Endian order\n")
    out_file.write(render_uint32(bitmap_layout_id.value))
    out_file.write(f" // L{bit_depth} format\n")
    out_file.write(render_uint32(bitmap_linestride))
    out_file.write(f" // Linestride ({padded_image_width} * {bit_depth}bpp / 8)\n")
    out_file.write(render_uint32(padded_image_width))
    out_file.write(" // Font width\n")
    out_file.write(render_uint32(glyph_height))
    out_file.write(" // Font height\n")
    out_file.write(render_uint32(0))
    out_file.write(" // Bitmap pointer in RAM\n")
    out_file.write("};\n")

run()