from PIL import Image
from utils import *

def run():
  input_filename = "in.png"
  bitmap_name = "NAME"
  output_filename = "progmem.hpp"
  bit_depth = 1
  indent_spaces = 2
  bitmap_byte_columns = 10

  # FIXME: Pad image width to round bytes per line

  image = Image.open(input_filename)
  (image_width, image_height) = image.size

  image = image.convert('L')
  bitmap_data = change_bit_depth(image.getdata(), bit_depth)
  (bitmap_bytes, bitmap_byte_count) = join_to_bytes(bitmap_data, bit_depth)
  bitmap_layout = bit_depth_to_l_layout(bit_depth)

  with open(output_filename, "w") as out_file:
    out_file.write(f"const uint16_t BITMAP_{bitmap_name}_WIDTH = {image_width};\n")
    out_file.write(f"const uint16_t BITMAP_{bitmap_name}_HEIGHT = {image_height};\n")
    out_file.write(f"const auto BITMAP_{bitmap_name}_LAYOUT = {bitmap_layout.value};  // {bitmap_layout.name}\n")
    out_file.write(f"const uint32_t BITMAP_{bitmap_name}_BYTE_COUNT = {bitmap_byte_count};\n")
    out_file.write(f"const uint8_t BITMAP_{bitmap_name}_BYTES[] PROGMEM = {{\n")
    out_file.write(render_byte_list(bitmap_bytes, bitmap_byte_columns, indent_spaces))
    out_file.write("\n};\n")

run()