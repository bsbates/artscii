from __future__ import division
from colorsys import rgb_to_hls
from colorsys import hls_to_rgb
from optparse import OptionParser
from PIL import Image

import sys


def ascii_for_luminance(luminance, luminances):
    closest = 0
    closest_distance = 100000
    for code in luminances:
        difference = abs(luminance - luminances[code])
        if difference < closest_distance:
            closest = code
            closest_distance = difference
    return closest


def ascii_and_color_for_region(region, luminances):
    # Do a simple average of HSL.
    # Use the L to determine which character to use
    # Use RGB average for the actual letter color
    # This should give a mix of whitespace and color to represent the cell
    source = region.load()
    total_h, total_s, total_l = (0,0,0)
    total_r, total_g, total_b = (0,0,0)
    region_x, region_y = region.size
    total_pixels = region_x * region_y
    for x in range(region_x):
        for y in range(region_y):
            r, g, b, a = source[x,y]
            h, l, s = rgb_to_hls(r/255, g/255, b/255)
            total_h += h
            total_l += l
            total_s += s
            total_r += r
            total_g += g
            total_b += b
    avg_h, avg_l, avg_s = (total_h/total_pixels, total_l/total_pixels, total_s/total_pixels)

    letter = ascii_for_luminance(avg_l, luminances)
    color_percentage = hls_to_rgb(avg_h, avg_l, avg_s)
    return (letter, (total_r/total_pixels, total_g/total_pixels, total_b/total_pixels))


def get_ascii_letter_image(code, ascii_image, letter_size):
    letter_size_x, letter_size_y = letter_size
    image_size_x, image_size_y = ascii_image.size
    letters_per_row = image_size_x // letter_size_x
    letter_row = code // letters_per_row
    letter_column = code % letters_per_row

    bounds = (letter_column*letter_size_x, 
        letter_row*letter_size_y, 
        letter_column*letter_size_x + letter_size_x, 
        letter_row*letter_size_y + letter_size_y)

    return ascii_image.crop(bounds)


def luminance_for_ascii_letter(letter_image):
    source = letter_image.load()
    total_pixels = letter_image.size[0] * letter_image.size[1]
    lum_pixels = 0
    for x in range(letter_image.size[0]):
        for y in range(letter_image.size[1]):
            sr, sg, sb, sa = source[x,y]
            if sa > 0:
                lum_pixels += 1
    luminance = (lum_pixels*2) / total_pixels
    return luminance


def build_luminance_dict(ascii_image, letter_size):
    luminances = {}
    ##TODO: Ability to manually set the ascii palette
    for ascii in range(32, 108):
        letter_image = get_ascii_letter_image(ascii, ascii_image, letter_size)
        luminances[ascii] = luminance_for_ascii_letter(letter_image)
    print luminances
    return luminances


def color_ascii_letter_image(letter_image, rgb):
    source = letter_image.load()
    r, g, b = rgb

    for x in range(letter_image.size[0]):
        for y in range(letter_image.size[1]):
            sr, sg, sb, sa = source[x,y]
            if sa > 0:
                source[x,y] = (int(r),int(g),int(b),255)
            else:
                source[x,y] = (255,255,255,0)


##
# Option Parsing

usage = "usage: artscii [options] INPUT_FILE OUTPUT_FILE";
parser = OptionParser(usage=usage)
parser.add_option('-x', '--chunkx', dest="chunk_size_x", default=16)
parser.add_option('-y', '--chunky', dest="chunk_size_y", default=32)
parser.add_option('-a', '--ascii_image', dest="ascii_image_filename", default='ascii-8x16.png')
parser.add_option('-i', '--letter_x', dest="letter_x", default=8)
parser.add_option('-j', '--letter_y', dest="letter_y", default=16)
(options, args) = parser.parse_args();

if len(args) < 2:
    print usage
    sys.exit(1)

input_filename = args[0];
output_filename = args[1];

raw_ascii_image = Image.open(options.ascii_image_filename)
print 'Ascii image:'
print(raw_ascii_image.format, raw_ascii_image.size, raw_ascii_image.mode)

ascii_image = raw_ascii_image.convert('RGBA')
print 'Ascii converted:'
print(ascii_image.format, ascii_image.size, ascii_image.mode)

raw_input_image = Image.open(input_filename)
print 'Raw:'
print(raw_input_image.format, raw_input_image.size, raw_input_image.mode)

rgb_input_image = raw_input_image.convert('RGBA')
print 'Converted:'
print(rgb_input_image.format, rgb_input_image.size, rgb_input_image.mode)

# Determine dimensions
input_x, input_y = rgb_input_image.size
chunk_x, chunk_y = (int(options.chunk_size_x), int(options.chunk_size_y))
letter_size_x, letter_size_y = (int(options.letter_x), int(options.letter_y))

cells_x = (input_x - chunk_x) // chunk_x
cells_y = (input_y - chunk_y) // chunk_y

luminances = build_luminance_dict(ascii_image, (letter_size_x, letter_size_y))

# Create output image
output_image = Image.new("RGBA", (cells_x * letter_size_x, cells_y * letter_size_y), 'white')
print 'Output image:'
print(output_image.format, output_image.size, output_image.mode)

for cell_x in range(cells_x):
    cell_left = cell_x * chunk_x
    cell_right = cell_left + chunk_x
    output_left = cell_x * letter_size_x
    output_right = output_left + letter_size_x

    for cell_y in range(cells_y):
        cell_top = cell_y * chunk_y
        cell_bottom = cell_top + chunk_y
        output_top = cell_y * letter_size_y
        output_bottom = output_top + letter_size_y

        cell_coordinates = (cell_left, cell_top, cell_right, cell_bottom)
        cell = rgb_input_image.crop(cell_coordinates)

        ascii_code, color = ascii_and_color_for_region(cell, luminances)
        letter_image = get_ascii_letter_image(ascii_code, ascii_image, (letter_size_x, letter_size_y))
        color_ascii_letter_image(letter_image, color)

        output_image.paste(letter_image, (output_left, output_top, output_right, output_bottom))

        sys.stdout.write('.')

print "Saving..."
output_image.save(output_filename)
print "Done!"

