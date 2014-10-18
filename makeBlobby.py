#!/bin/env python

# path shenanigans
import sys
import os.path as p  # not to be confused with sys.path
def addToPath(searchPath):
    if searchPath not in sys.path:
        sys.path.append(searchPath)
path_this = p.expanduser('~/teamCandy/MayaToPbrt/')
addToPath(path_this)


###### config ######

recompileOnLoad = False

###### end config ######

path_polygonizer_build  = p.join(path_this, 'polygonizer/build')
path_polygonizer        = p.join(path_this, 'polygonizer/build/Main')
path_default_bloomy     = p.join(path_this, 'polygonizer/bloomies/generated.bloomy')
path_default_obj        = p.join(path_this, 'polygonizer/OBJs/bloomy.obj')

import numpy as np
import subprocess

# compile the polygonizer
if recompileOnLoad or not p.exists(path_polygonizer):
    print 'compiling the polygonizer...'
    subprocess.Popen(['cmake', '../src/'], cwd=path_polygonizer_build).communicate()
    subprocess.Popen(['make', 'clean'],    cwd=path_polygonizer_build).communicate()
    subprocess.Popen(['make'],             cwd=path_polygonizer_build).communicate()
    print 'done compiling. '
assert p.exists(path_polygonizer)









template_file = '''
Constant(
    -0.5
)

{}
'''


template_ball = '''
Translate(
    {} {} {}
    Sphere(
        {}
    )
)
'''

template_dent = '''
Translate(
    {} {} {}
    Sphere(
        {}
    )
)
'''



# takes a bloomy file and writes an obj to the second file path
def polygonize(path_bloomy, path_obj, polygonSpacing=None):

    # adjust polygonSpacing if needed
    if polygonSpacing:
        # appending to the file
        # not the most effictient way of doing things but it works
        with open(path_bloomy, 'a') as f:
            # we assume there is a \n at the end of the file.
            f.write('#SETVAR polygonSpacing {}\n'.format(polygonSpacing))


    # os.system("{} {} {}".format(path_polygonizer, path_bloomy, path_obj))
    programArgs = [path_polygonizer, path_bloomy, path_obj]
    subprocess.Popen(programArgs).communicate()
    if not p.exists(path_obj):
        raise Exception("polygonization failed: " + ' '.join(programArgs))

    print 'polygonised {} to {}'.format(path_bloomy.split('/')[-1], path_obj.split('/')[-1])

def exportBloomy(radii, positions, path_obj, polygonSpacing, path_bloomy=None):
    if path_bloomy == None:
        path_bloomy = path_default_bloomy

    balls = []
    for radius, position in zip(radii, positions):
        balls.append(template_ball.format(
            position[0],
            position[1],
            position[2],
            radius
        ))

    bloomy = template_file.format(''.join(balls))

    with open(path_bloomy, 'w') as f:
        f.write(bloomy)

    polygonize(path_bloomy, path_obj, polygonSpacing)


def makeBlob_uniformDistribution(path_obj, polygonSpacing=0.07):
    numBalls = np.random.randint(2,18);
    radii     = np.random.uniform(0.30, 0.35, (numBalls,))
    positions = np.random.uniform(-.5, 0.5, (numBalls, 3))
    exportBloomy(radii, positions, path_obj, polygonSpacing)

def makeBlob_iterStep(path_obj, radii, positions, sphericalness, polygonSpacing, path_bloomy=None):
    exportBloomy(radii, positions, path_obj, polygonSpacing, path_bloomy)  # change None to polygonSpacing to get higher quality inconsistent blob

    # open the polygonized thing
    with open(path_obj) as f:
        verts = np.array([
            map(float, line.split()[1:])
            for line in f if line.startswith('v')
        ])

    # choose a position and add it to the list
    if len(positions) > 0:
        average = verts.mean(0)
        position = (
            (1-sphericalness) * verts[np.random.randint(0,len(verts))] +
            (  sphericalness) * average
        )
    else:
        position = np.array([0,0,0])

    # print 'seed:', np.random.randint(3,999), np.random.randint(3,999), position, positions
    return position

# yields the percentage increment of progress done
def makeBlob_iter(path_obj, sphericalness=0.5, radiusMin=0.20, radiusMax=0.25, polygonSpacing=0.07, numBalls=None, seed=None, path_bloomy=None):
    if seed != None:
        import random
        random.seed(seed)
        np.random.seed(seed)
    if not numBalls:
        numBalls = np.random.randint(2, 18)


    progress = 0.0
    radii     = np.random.uniform(radiusMin, radiusMax, (numBalls,))
    positions = [np.array([0,0,0])]
    for i in xrange(numBalls-1):
        positions.append(
            makeBlob_iterStep(path_obj, radii, positions, sphericalness, polygonSpacing, path_bloomy)
        )
        prevProgress = progress
        progress = 100.0 * (float(i+1) / float(numBalls+1))
        # yield progress - prevProgress
        yield progress


    exportBloomy(radii, positions, path_obj, polygonSpacing, path_bloomy)


    # we are done
    # yield 100.0 - progress
    yield 100.0
    print 'made a nerd with {} balls.'.format(numBalls)

# a wrapper to call makeBlob_iter until it is done
def makeBlob(*args, **kwargs):
    percentage = 0.0
    for increment in makeBlob_iter(*args, **kwargs):
        percentage += increment
        # print "blob progress:", percentage


# moves all vertices such that the average is at (0 0 0)
def centerObj(path_obj):
    with open(path_obj) as f:
        lines = f.readlines()
    vertices = np.array([ map(float, line.split()[1:]) for line in lines if line.startswith('v ' )])
    mean = vertices.mean(0) # remove the average
    print 'removing mean: ', mean
    vertices -= mean

    # replace the vertices in the lines
    vertexIndex = 0
    for i in xrange(len(vertices)):
        if (lines[i].startswith('v ')):
            lines[i] = 'v {}\t{}\t{}\n'.format(*vertices[vertexIndex])
            vertexIndex += 1

    with open(path_obj, 'w') as f:
        f.write(''.join(lines))


if __name__ == '__main__':
    # makeBlob_uniformDistribution(path_default_obj)
    makeBlob(path_default_obj)