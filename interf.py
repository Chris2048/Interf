#!/usr/bin/env python2.7

import os
from os.path import join as joinpath
import numpy
from datetime import datetime as dt
from PIL import Image
from math import pi, sqrt, cos
from collections import namedtuple
import plac
from clint.textui import progress
#from clint import args
#from clint.textui import puts, colored, indent

# inspired by http://lybniz2.sourceforge.net/safeeval.html
safe_funs = ['cos', 'cosh', 'e', 'exp', 'log', 'log10', 'pi', 'sin', 'sinh',
    'tan', 'tanh']
safe_funs = dict([(k, locals().get(k, None)) for k in safe_funs])
safe_funs['abs'] = abs


def value_at_point(base, x, y, zoom, time):
    # maybe move this elsewhere? like a 'HACKING' file (dev docs) or possibly
    # with the tests once corresponding tests have been created. # TODO
    '''Returns an integer value in [0,256) representing a pixel value fmod and
    zoom are used to 'zoom' in and out. Infact, what happens is the resolution
    stays the same, the points are just moved closer together and centered;
    then the frequency is modified so the relative distances are the same,
    e.g. If I use zoom = 2, the point co-ordinates are all halved, moving the
    points closer to each other and centered; then, The 'travel' is adapted
    accordingly to ensure the waves move slower across a (relatively) larger
    area (but with frequencies unchanged).

   01234567890123456789        01234567890123456789       01234567890123456789
   --------------------        --------------------       --------------------
 0|x(0,0)              |     0|x(0,0) .(0,7)       |    0|     |              |
 1|         (1,15).    |     1| .(1,1)             |    1|     |              |
 2|                    |     2|     .(2,5)         |    2|-----x(2,5) .(2,12) |
 3|   .(3,3)           | ->  3|                    | -> 3|      .(3,6)        |
 4|                    | ->  4|                    | -> 4|          .(4,10)   |
 5|           .(5,11)  |     5|                    |    5|                    |
 6|                    |     6|                    |    6|                    |
 7|                    |     7|                    |    7|                    |
   --------------------        --------------------       --------------------

     (1,15) <2,16>       ->        <1,8> (0,7)       ->         (2,12)
      (3,3) <4,4>        ->        <2,2> (1,1)       ->         (3,6)
     (5,11) <6,12>       ->        <3,6> (2,5)       ->         (4,10)
    '''
    # FIXME For some reason, I can see a spiral pattern in the darker patterns,
    # need to figure out why... the 'total cancellation' seem to rule out error
    # in that simple case, maybe the error of sin changes e.g. with frequency?
    global points
    contrib = []
    for p in base.points:
        distx = (2 * p.x + base.x * (zoom - 1)) / (zoom * 2)
        disty = (2 * p.y + base.y * (zoom - 1)) / (zoom * 2)
        # a^2 + b^2 = c^2
        dist = sqrt((x - distx) ** 2 + (y - disty) ** 2)  # in pixels
        dist = (zoom * dist) / base.travel  # in ms, adjusted for zoom
        totaltime = time + dist  # time at source+base.travel time=total time
        aphase = (totaltime * p.w) / 1000.0  # phase change during this time
        totalphase = p.p + aphase  # initial phase+addition phase=total phase
        val = cos(2 * pi * totalphase)
        contrib.append(val)
    return abs(sum(contrib))


def gen_pmap(base, zoom, time):
    '''Generates a numpy array representing the image
     Returns the numpy array.'''
    pmap = numpy.zeros((base.x, base.y, 3)).astype('uint8')
    scale = (255.0 / len(base.points))
    for x in range(base.x):
        for y in range(base.y):
            val = scale * value_at_point(base, x, y, zoom, time)
            pmap[x, y, 0] = val
            pmap[x, y, 1] = val
            pmap[x, y, 2] = val
    return pmap


# TODO calculate length for fixed strings of the form "%03d", or "%3d"
def generate_pics(base):
    timestamp = dt.now().strftime("%Y%m%d%H%M%S")  # TODO make this optional?
    frames = base.l / base.ft
    safe_funs['N'] = frames
    for n in progress.bar(range(1, frames + 1)):
        safe_funs['n'] = float(n)
        # potentially unsafe, see comment above 'safe_fun'
        zoom = eval(base.zs, {"__builtins__": None}, safe_funs)
        # DEBUG
        #print "%3d/%d" % (n, frames),
        #t = dt.now()
        pmap = gen_pmap(base, zoom, n * base.ft)
        # DEBUG
        #dura = (dt.now()-t).microseconds
        #print "%3d,%03dms" % (dura/1000, dura%1000)
        Image.fromarray(pmap).save(joinpath(base.tp, '%s-%03d.png') \
                % (timestamp, n))
    print '''Now use 'apngasm <filepath>/<filename>.png %s/%s*.png 1 %d' to
        create the animated png!''' % (base.tp, timestamp, base.resolution)


class Base():
    'class representing base values'

    def __init__(self, x, y, ft, l, tp, zs):
        self.x = x
        self.y = y
        self.ft = ft
        self.l = l
        self.tp = tp
        self.zs = zs
        self.points = []

    class Point(namedtuple('Point', 'base, gx gy w p')):
        '''class representing point source in image.
        gx,gy are co-ordinates of point,
        w is wavelength in revolutions per second,
        p is initial phase of point in turns'''
        __slots__ = ()

        @property
        def x(self):
            return int(self.gx * self.base.x)

        @property
        def y(self):
            return int(self.gy * self.base.y)

    @property
    def travel(self):
        'pixel distance covered in a millisecond'
        return self.y / 1000.0

    @property
    def resolution(self):
        '''value for x in 1/x representing frametime as a fraction of a second,
        for use as an argument to apngasm'''
        return 1000 / self.ft

    def addPoint(self, gx, gy, w, p):
        self.points.append(self.Point(self, gx, gy, w, p))


@plac.annotations(
    x_size=('height of image, in pixels', 'option', 'x', int),
    y_size=('width of image in pixels', 'option', 'y', int),
    tmp_path=('temporary path to save files in', 'option'),
    zoom_string=('''
    Python expression representing how the animation should zoom, use 'n' to
    represent the image number, and 'N' for the total number of frames
    ''', 'option', 'z', None, None, 'ZOOM_STRING'),
    length=('''
    How long the animation should be, in milliseconds (relative to base.ft)
    ''', 'option', 'l', int),
)  # Can I make y_size depend on x_size?
def main(x_size=60, y_size=120, tmp_path=os.path.expanduser('~/intpics'),
        zoom_string='4', length=2000):
    "Generate a series of png files from which to create an apng file."
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
    base = Base(y_size, x_size, 100, length, tmp_path, zoom_string)
    # TODO point are fixed, add way to specify them - maybe from csv format?
    base.addPoint(1.0 / 2, 1.0 / 8, 1.0 / 4, 0.75)
    base.addPoint(1.0 / 3, 3.0 / 5, 1, 0.5)
    base.addPoint(1.0 / 8, 2.0 / 5, 1.0 / 3, 1)
    generate_pics(base)

if __name__ == '__main__':
    plac.call(main)
