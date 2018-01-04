"""
Island heightmap generator using Julia set and Simplex noise.
Copyright (C) 2018  Minimata

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Minimata
@EpicMinimata
Alexandre Serex
serex.alexandre@gmail.com
"""



import random, math
from PIL import Image, ImageDraw
from vector2d import Vector
from noise import snoise2

"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!! GENERAL CONTROL !!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""

"""
Initialize the randomness.

The values origin and the ones in the list simplex_offsets are used for the different simplex noises we're going to generate for the domain warping.
They need to be consistent throughout each warping process.
"""
random.seed()
origin = random.uniform(-10000, 10000)
simplex_offsets = []

"""
Image initialization. We're using a size of 1024x1024 by default.
"""
imgx = 1024
imgy = 1024
image = Image.new("RGB", (imgx, imgy))


def final_changes(data):
    """
    This function gives you control over the data outputed by the update_julia function.
    Basically the final changes before drawing it, in this state of the program.

    What I do here is add a little more salt, in the form of a ponderated average on some levels with another set of warped noise.
    """
    salt = update_warp(freq=1.0)
    salt = scale_list(salt, 255.0)

    final = []
    for i, d in enumerate(data):
        if d > 0:
            # we add the salt noise proportionally to the mountain height (the lower, the more salt)
            final.append((3.0 * d + salt[i] * (255.0 / (2.0*(2.0 * 255.0 + d)))) / 4.0)
        else:
            final.append(d)

    return final


"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!! FRACTAL CONTROL !!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""

"""
max_it is the number of iterations we're doing for the julia set without breaking.
Lower values give faster results and wider white areas, but lower fractal definition.

num_frac is the number of fractals we're going to mix up between each other to create the final image.

ponderation_basis is a factor that will be used to randomize the ponderation of the fractals between each other.
"""
max_it = 20
num_frac = 6


def make_complex(re1=-0.1, re2=0.0, im1=0.9, im2=1.0):
    """
    This is a helper to create a complex number that might be random, depending on the given bounds given to it.
    I use this function to create the different constant values that are added to Z in the julia function.
    I found these default values to give the best results, since the julia set of c = 0 + 1j looks the morst like some mountain.
    Also, it's way more predictable than anything else.
    """
    x = random.uniform(re1, re2)
    y = random.uniform(im1, im2)
    return x + y * 1j


def create_z(x, y, rand):
    """
    This creates a number that is rotated, scaled and translated all base on a single random number.
    It's used to apply these transformations to the Julia fractals we're going to use for our noise.
    """
    alpha = 2.0 * math.pi * rand
    scale = clamp(2.0 * rand, 0.2, 2.0)
    trans = (rand * 2.0 - 1.0) * 0.2
    zx = ((x * math.sin(alpha) + y * math.cos(alpha)) + trans) * scale
    zy = ((x * math.cos(alpha) - y * math.sin(alpha)) + trans) * scale
    return zx + zy * 1j


def warp_to_julia(warp_value):
    """
    This function converts the float value of the warped noise at some point (x, y) (so between -1 and 1) to return a float.
    The returned value will be used by the julia function as it's limit.

    You can play with this function a bit to see how it changes the island.
    Try to keep the return value positive though.
    A nice one is to replace the math.fabs by a putting the value to a power of 2.
    It gives you an less flat island, with cliffs and stuff.
    """
    # return (2.0 * warp_value) ** 2  # more cliffs
    return 2.0 * math.fabs(warp_value) ** 0.3  # more flat (don't try on your girlfriend)


"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!! NOISE CONTROL !!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""

"""
island_height represent the factor given to the island height at it's center.

radius_offset is the value by which the raidus of the island is reduced to give a smaller island.
"""

island_height = 20.0
radius_offset = 0.0
num_warpings = 2  # This represents the number of warpings we're going to do. 2 is usually enough.


def transform_warp(x, y, simplex):
    """
    This function gives you control over the noise you're going to feed to the Julia set for it's limits.
    It's inputed with the simplex value for the position(x, y)

    What I've done here is giving it a factor that depends on the distance to the center of given point (x, y).
    So basically, making the noise 0 at the edge of the island and island_height at the center of it.
    """
    dist_center = math.sqrt((x - imgx / 2) ** 2 + (y - imgy / 2) ** 2) / (imgx / 2)
    island_radius = (dist_center + radius_offset)
    factor = 1 - (island_radius ** 2)
    factor *= island_height
    if island_radius > 1:
        factor = 0
    simplex *= factor

    return simplex


"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!! FRACTAL CORE !!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""


def clamp(value, min_value, max_value):
    """
    A helper to clamp a value between two others.
    """
    return max(min(value, max_value), min_value)


def julia(z, c, limit=2.0):
    """
    This function iterates over a given position in the gaussian plan and returns the number of iterations needed to either :
     - reach the maximum number of iterations allowed by max_it
     - reach the limit, 2.0 by default but defined by our simplex noise for our island generation.
    """
    i = 0
    for i in range(int(max_it)):
        if abs(z) > limit:
            break
        z = z * z + c
    return i


def update_julia(warp_data=None, rang=1):
    """
    This is the main julia calculations function.

    warp_data is where we put the noise to create our island with.
    rang is juste the range of the output (by default from -1 - 1j to 1 + 1j).
    """
    xa = -rang
    xb = rang
    ya = -rang
    yb = rang

    color = []  # Holds our final color for this batch
    cs = []  # collection of the c numbers we need for each fractal
    zs_rand = []  # list of the random numbers used to transform our z-coordinates with the create_z function

    # lets populate our constant and Z-seeds
    for i in range(num_frac):
        cs.append(make_complex())
        zs_rand.append(random.random())

    count = 0
    print("Creating the Julia set data...")
    for y in range(imgy):
        zy = y * (yb - ya) / (imgy - 1) + ya
        for x in range(imgx):
            zx = x * (xb - xa) / (imgx - 1) + xa

            # Here we're doing an average of all our fractals.
            v = 0.0
            for i in range(num_frac):
                if warp_data is not None:
                    v += julia(create_z(zx, zy, zs_rand[i]), cs[i], warp_to_julia(warp_data[count]))
                else:
                    v += julia(create_z(zx, zy, zs_rand[i]), cs[i])
            v /= num_frac
            color.append(v)
            count += 1
    return color


"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!! NOISE CORE !!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""


def fbm(vec, octaves=8, freq=4.0):
    """
    Simple wrapper for the function we're using from the noise library.
    """
    return snoise2(vec.x / freq, vec.y / freq, octaves=octaves, base=origin)


def warp(p, freq=4.0):
    """
    This is the core warp function, gotten from Inigo Quilez ( <3 )

    It takes a position (as a vector) on entry.
    Returns a float value between -1 and 1.
    The more warping, the closer to 0 the value will get, so scale it up before writing it to an image.
    """
    updated_value = 0.0
    for i in range(num_warpings):
        off1 = simplex_offsets[2 * i]
        off2 = simplex_offsets[2 * i + 1]
        updated_value = Vector(fbm(p + updated_value * 4.0 + Vector(off1[0], off1[1]), freq=freq),
                               fbm(p + updated_value * 4.0 + Vector(off2[0], off2[1]), freq=freq))
    return fbm(p + updated_value * 4.0, freq=freq)


def seed_warp():
    """
    This function is called between each update_warp to have some random simplex positions and create different noise each time.
    """
    global simplex_offsets
    simplex_offsets = []
    for i in range(2 * num_warpings):
        simplex_offsets.append((random.uniform(-10000, 10000), random.uniform(-10000, 10000)))


def update_warp(freq=4.0):
    """
    This is the function calculating our base warped noise.

    It gets the value from the core warp function, lets you modify it as you wish, and return all of the values for the image.
    """
    data_warp = []
    seed_warp()
    print("Creating some warped noise...")
    for y in range(imgy):
        for x in range(imgx):
            simplex = warp(Vector(x / imgx, y / imgy), freq=freq)
            simplex = transform_warp(x, y, simplex)
            data_warp.append(simplex)
    return data_warp


"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!! GENERAL CORE !!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""


def draw(data, filename="island.png"):
    """
    This function draws the given data as a 1d list to the image.
    """
    draw_data = scale_list(data, 255.0)

    data_xy = []
    for y in range(imgy):
        for x in range(imgx):
            data_xy.append((x, y))

    im = ImageDraw.Draw(image)
    for i, p in enumerate(data_xy):
        color = int(math.fabs(draw_data[i]))
        im.point(p, fill=(color, color, color))
    del im
    image.save(filename, "PNG")
    print("Saved image as {0}.".format(filename))


def scale_list(l, max_value):
    """
    This simple helper scales every item of a list by the necessary factor to the maximum value of the list reaches max_value.
    Not really suited as is for list containing negative values.
    """
    factor = max_value / max(l)
    return [d * factor for d in l]


"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!! MAGIC HAPPENS HERE !!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""

# We first make a domain warped noise image that we (badly) scale up to a (-1, 1) range.
data = update_warp()
data = scale_list(data, 1.0)  # not perfect since there are negative values in data
# draw(data, filename="noise.png")  # if we want to have a look at our warped noise

# We then feed that data to the julia set
data = update_julia(data)
data = scale_list(data, 255.0)
# draw(update_julia(), filename="julia.png")  # if we want to take a look at some fractals without noise

# our final changes to the data, and final draw
draw(final_changes(data))
