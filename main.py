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
from vector import Vector
from noise import snoise2


"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!! GENERAL CONTROL !!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""


"""
Image initialization. We're using a size of 1024x1024 by default here.
"""
imgx = 1024
imgy = 1024


"""
Values for noise control
"""

island_noise_frequency = 7.0  # Frequency of the base noise used for the island. The higher, the smoother the island is.
radius_offset = 0.0  # Value by which the radius of the island is reduced.

num_warpings = 2  # This represents the number of warpings we're going to do. 2 is usually enough.

noise_sharpness = 0.4  # value by which the noise is put to the power of. Higher = more cliffs, lower = more flat island

"""
Values for fractal control
"""

max_it = 24  # Max number of iterations before breaking for the Julia set calculations
num_frac = 8  # Number of fractals we're going to use

constant_re_low = -0.1  # Lower bound of the random real value of the constant that's being added in the Julia function
constant_re_high = -0.1  # Higher bound of the random real value of the constant that's being added in the Julia function
constant_im_low = 0.9  # Lower bound of the random imaginary value of the constant that's being added in the Julia function
constant_im_high = 1.1  # Higher bound of the random imaginary value of the constant that's being added in the Julia function

scale_value_low = 0.2  # Lower bound of the randomized scale value of the fractals
scale_value_high = 2.0  # Higher bound of the randomized scale value of the fractals
trans_max_value = 0.2  # Higher value by which the fractal can be transitioned
rotation_max_value = 1.0  # Higher value by which the fractal can be rotated


"""
Values for final changes control
"""

salt_frequency = 1.0  # frequency of the final layer of salt
low_barrier = 4  # Value under which the final height value will be 0. Keep between 0 and 255
weight_base = 2.0  # weight of the base layer of the island opposing the salt
weight_salt = 1.0  # weight of the salt layer added to the island


"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!! FRACTAL CORE !!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""


def create_z(x, y, rand):
    """
    This creates a number that is rotated, scaled and translated all base on a single random number.
    It's used to apply these transformations to the Julia fractals we're going to use for our noise.
    """
    alpha = 2.0 * math.pi * rand * rotation_max_value
    scale = clamp(scale_value_high * rand, scale_value_low, scale_value_high)
    trans = (rand * 2.0 - 1.0) * trans_max_value
    zx = ((x * math.sin(alpha) + y * math.cos(alpha)) + trans) * scale
    zy = ((x * math.cos(alpha) - y * math.sin(alpha)) + trans) * scale
    return zx + zy * 1j


def make_complex(re1=constant_re_low, re2=constant_re_high, im1=constant_im_low, im2=constant_im_high):
    """
    This is a helper to create a complex number that might be random, depending on the given bounds given to it.
    I use this function to create the different constant values that are added to Z in the julia function.
    I found these default values to give the best results, since the julia set of c = 0 + 1j looks the morst like some mountain.
    Also, it's way more predictable than anything else.
    """
    x = random.uniform(re1, re2)
    y = random.uniform(im1, im2)
    return x + y * 1j


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

            # Here we're keeping the max value of each fractal for each point
            vs = []
            for i in range(num_frac):
                if warp_data is not None:
                    vs.append(julia(create_z(zx, zy, zs_rand[i]), cs[i], warp_to_julia(warp_data[count])))
                else:
                    vs.append(julia(create_z(zx, zy, zs_rand[i]), cs[i]))
            v = max(vs)
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


def fbm(vec, octaves=8, freq=5.0):
    """
    Simple wrapper for the function we're using from the noise library.
    """
    return snoise2(vec[0] / freq, vec[1] / freq, octaves=octaves, base=origin)


def warp(p, freq=5.0):
    """
    This is the core warp function, gotten from Inigo Quilez ( <3 )

    It takes a position (as a vector) on entry.
    Returns a float value between -1 and 1.
    The more warping, the closer to 0 the value will get, so scale it up before writing it to an image.
    """
    updated_value = Vector(0, 0)
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
    if island_radius > 1:
        factor = 0
    simplex *= factor

    return simplex


def warp_to_julia(warp_value):
    """
    This function converts the float value of the warped noise at some point (x, y) (so between -1 and 1) to return a float.
    The returned value will be used by the julia function as it's limit.

    You can play with this function a bit to see how it changes the island.
    Try to keep the return value positive though.
    """
    return 2.0 * math.fabs(warp_value) ** noise_sharpness  # more flat (don't try on your girlfriend)


def update_warp(freq=5.0):
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
!!!!!!!!!!!!! NORMALS & GRADIENT !!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""


def get_face_normal(center, p1, p2):
    first = p1 - center
    second = p2 - center
    return first ** second


def create_normals(values):
    normals = []
    count = 0
    print("Creating normals...")
    for x in range(imgx):
        for y in range(imgy):
            normal = Vector(0.0, 0.0, 0.0)
            center = Vector(x, y, values[count])
            if 0 < x < imgx - 1 and 0 < y < imgy - 1:
                normal += get_face_normal(center, Vector(x-1, y-1, values[count - imgy - 1]), Vector(x, y-1, values[count - imgy]))
                normal += get_face_normal(center, Vector(x, y-1, values[count - imgy]), Vector(x+1, y-1, values[count - imgy + 1]))
                normal += get_face_normal(center, Vector(x+1, y-1, values[count - imgy + 1]), Vector(x+1, y, values[count + 1]))
                normal += get_face_normal(center, Vector(x+1, y, values[count + 1]), Vector(x+1, y+1, values[count + imgy + 1]))
                normal += get_face_normal(center, Vector(x+1, y+1, values[count + imgy + 1]), Vector(x, y+1, values[count + imgy]))
                normal += get_face_normal(center, Vector(x, y+1, values[count + imgy]), Vector(x-1, y+1, values[count + imgy - 1]))
                normal += get_face_normal(center, Vector(x-1, y+1, values[count + imgy - 1]), Vector(x-1, y, values[count - 1]))
                normal += get_face_normal(center, Vector(x-1, y, values[count - 1]), Vector(x-1, y-1, values[count - imgy - 1]))
            else:
                normal = Vector(0.0, 0.0, 1.0)
            normals.append(normal.normalize())
            count += 1
    return normals


def create_gradient_from_normals(normals):
    gradients = []
    print("Creating gradients...")
    for normal in normals:
        if normal[2] > 0:
            gradients.append(Vector(normal[0] / normal[2], normal[1] / normal[2], 0.0))
        else:
            gradients.append(Vector(normal[0], normal[1], 0.0).normalize())
    return gradients


def draw_from_vectors(normals, filename="island_normals.png"):
    """
    This function draws the given data as a 1d list to the image.
    """
    red, green, blue = [list(x) for x in zip(*normals)]
    red = scale_list(red, 255.0)
    green = scale_list(green, 255.0)
    blue = scale_list(blue, 255.0)

    im = ImageDraw.Draw(image)
    for i, p in enumerate(data_xy):
        im.point(p, fill=(int(red[i]), int(green[i]), int(blue[i])))
    del im
    image.save("images/" + filename, "PNG")
    print("Saved normals as {0}.".format(filename))


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

    im = ImageDraw.Draw(image)
    for i, p in enumerate(data_xy):
        color = int(math.fabs(draw_data[i]))
        im.point(p, fill=(color, color, color))
    del im
    image.save("images/" + filename, "PNG")
    print("Saved image as {0}.".format(filename))


def scale_list(l, max_value):
    """
    This simple helper scales every item of a list by the necessary factor to the maximum value of the list reaches max_value.
    Not really suited as is for list containing negative values.
    """
    if max(l) <= 0.0:
        return [0] * len(l)
    factor = max_value / max(l)
    return [d * factor for d in l]


def add_salt(data):
    """
    This function gives you control over the data outputed by the update_julia function.
    Basically the final changes before drawing it, in this state of the program.

    What I do here is add a little more salt, in the form of a ponderated average on some levels with another set of warped noise.
    """
    salt = update_warp(freq=salt_frequency)
    salt = scale_list(salt, 255.0)

    final = []
    for i, d in enumerate(data):
        if d > low_barrier:
            # we add the salt noise proportionally to the mountain height (the lower, the more salt)
            final.append((weight_base * d + weight_salt * (salt[i] * (255.0 / (2.0*(2.0 * 255.0 + d))))) / (weight_base + weight_salt))
        else:
            final.append(0)

    return final


"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!! MAGIC HAPPENS HERE !!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""


"""
Initialize some general value and the randomness.

The values origin and the ones in the list simplex_offsets are used for the different simplex noises we're going to generate for the domain warping.
They need to be consistent throughout each warping process.
"""

random.seed()
origin = random.uniform(-10000, 10000)
simplex_offsets = []
image = Image.new("RGB", (imgx, imgy))

data_xy = []
for y in range(imgy):
    for x in range(imgx):
        data_xy.append((x, y))


# We first make a domain warped noise image that we (badly) scale up to a (-1, 1) range.
data = update_warp(freq=island_noise_frequency)
data = scale_list(data, 1.0)  # not perfect since there are negative values in data
# draw(data, filename="noise.png")  # if we want to have a look at our warped noise

# We then feed that data to the julia set
data = update_julia(data)
data = scale_list(data, 255.0)
# draw(update_julia(), filename="julia.png")  # if we want to take a look at some fractals without noise

data = add_salt(data)
draw(data)

normals = create_normals(data)
draw_from_vectors(normals)
gradients = create_gradient_from_normals(normals)
draw_from_vectors(gradients, filename="island_gradients.png")



"""
Upcoming stuff
"""


"""
FVector ATerraGen::SetNormal(int32 x, int32 y, int XIndex, int YIndex) {
	TArray<FVector> vertices;
	for (int i = -1; i <= 1; i++) {
		for (int j = -1; j <= 1; j++) {
			int32 posX = x + i * CellSize;
			int32 posY = y + j * CellSize;
			int32 z = 0;
			if (XIndex == 0 || YIndex == 0 || XIndex == 2 * HalfWidth - 1 || YIndex == 2 * HalfWidth - 1) z = 0;
			else z = VerticesPos[XIndex + i][YIndex + j];
			vertices.Add(FVector(posX, posY, z));
		}
	}

	FVector normal(0, 0, 0);
	FVector center = vertices[4];

	normal += GetFaceNormal(center, vertices[0], vertices[1]);
	normal += GetFaceNormal(center, vertices[1], vertices[2]);
	normal += GetFaceNormal(center, vertices[2], vertices[5]);
	normal += GetFaceNormal(center, vertices[5], vertices[8]);
	normal += GetFaceNormal(center, vertices[8], vertices[7]);
	normal += GetFaceNormal(center, vertices[7], vertices[6]);
	normal += GetFaceNormal(center, vertices[6], vertices[3]);
	normal += GetFaceNormal(center, vertices[3], vertices[0]);

	normal.Normalize();
	return normal;
}

FVector ATerraGen::GetFaceNormal(FVector center, FVector i, FVector j) {
	FVector first = i - center;
	FVector second = j - center;
	return FVector::CrossProduct(second, first);
}
"""