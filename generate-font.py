import math
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


def join_to_bytes(data: Iterable[int], bit_depth: int) -> Tuple[Iterable[int], int]:
  data_list = list(data)
  data_length = len(data_list)

  if bit_depth == 8:
    return (data_list, data_length)
  
  if bit_depth == 4:
    if data_length % 2 == 1:
      data_list.append(0)
      data_length += 1

    bytes = list()
    i = 0
    while i < data_length:
      bytes.append(data_list[i] << 4 | data_list[i+1])
      i += 2
    
    return (bytes, int(data_length/2))
  
  raise ValueError("Supported bit depths are 4 and 8")


def render_byte_list(bytes: Iterable[int], byte_columns: int, indent_spaces: int = 2) -> str:
  output = " "*(indent_spaces-1)
  
  column = 0
  for byte in bytes:
    if column == byte_columns:
      output += "\n" + " "*(indent_spaces-1)
      column = 0
    column += 1
    output += f" {byte:#0{4}X},"

  return output.replace('X', 'x')


def bit_depth_to_layout(bit_depth: int) -> FT81xBitmapLayout:
  if bit_depth == 4:
    return FT81xBitmapLayout.L4
  
  raise ValueError('No matching bitmap layout')


# Settings

def run():
  image_width = 10 # This width will be padded based on bit depth, see 4.7.linestride in docs
  image_height = 18
  image_crop_top = 1
  font_size = 17
  font_file = "font.otf"
  font_x_adjust = 0.25
  font_y_adjust = 4
  rendering_scale = 4
  preview_filename = 'out.png' # None
  preview_only = True
  bit_depth = 4
  indent_spaces = 2
  bitmap_byte_columns = 10
  output_filename = 'progmem.hpp'

  padded_image_width = get_width_padded_to_bytes(image_width, bit_depth)
  canvas_width = rendering_scale * image_width
  canvas_height = rendering_scale * image_height

  glyph_width = image_width
  glyph_height = image_height - image_crop_top

  # End of settings


  # Build bitmap
  bitmap_bytes = list()
  bitmap_byte_count = 0

  preview_image = None
  if preview_filename:
    glyph_count = ord('~') - ord(' ') + 1
    preview_image = Image.new('L', size=(padded_image_width, glyph_height * glyph_count))

  font = ImageFont.truetype(font_file, rendering_scale*font_size, encoding="unic")

  for ascii_code in range(ord(' '), ord('~')+1):
    glyph = chr(ascii_code)

    # Render glyph
    image = render_glyph(
      glyph,
      font,
      image_height,
      image_crop_top,
      padded_image_width,
      rendering_scale,
      canvas_width,
      canvas_height,
      font_x_adjust,
      font_y_adjust)
    if preview_filename:
      preview_image.paste(image, (0, glyph_height*(ascii_code - ord(' '))))

    if preview_only:
      continue

    # Get output bytes
    glyph_data = change_bit_depth(image.getdata(), bit_depth)
    (glyph_bytes, glyph_byte_count) = join_to_bytes(glyph_data, bit_depth)
    bitmap_bytes.extend(glyph_bytes)
    bitmap_byte_count += glyph_byte_count

  if preview_filename:
    preview_image.save(preview_filename)
    if preview_only:
      exit()

  # Built font metrics
  metrics_width_bytes = [0]*ord(' ')                             # Skipped characters
  metrics_width_bytes.extend([image_width]*(ord('~')+1-ord(' ')+1))  # Rendered characters
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