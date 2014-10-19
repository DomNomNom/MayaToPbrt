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

path_pbrtExecutable = '~/teamCandy/comp408-project3/build/bin/pbrt'     # eg. '~/408/final/comp408-project3/bin/pbrt'
slowNormals = False

###### end config ######

assert path_pbrtExecutable
path_pbrtExecutable = p.expanduser(path_pbrtExecutable)


# basePath = p.expanduser('~/maya/2015-x64/plug-ins/MayaToPBRT-data')
# mayaSceneFile = basePath+'/cuube.ma'  # only needed in standalone



if __name__ == '__main__':
    print 'starting pymel...'  # A printout to say that we are starting

from pymel.core import *

import os
import glob
from itertools import product, izip_longest
import subprocess
import candyBox
import numpy as np
import base64

uniformScale = 1

# puts lineStart at the start of every line of the text
def indent(txt, indentLevel, indentChar='    '):
    lineStart = indentChar * indentLevel
    return lineStart + txt.replace('\n', '\n'+lineStart)

# [1,2,3] ==> '1 2 3'
def stringContents(iterable):
    return ' '.join(map(str, iterable))

def stringContents2D(matrix):
    return '\n'.join([ stringContents(row) for row in matrix ])


pbrtTemplate = '''
Scale -1 1 1
LookAt
    {camPos}
    {camLookAt}
    0 1 0

Camera "perspective"
    "float fov" [{camFov}]

PixelFilter "mitchell"
    "float xwidth" [2]
    "float ywidth" [2]

Sampler "bestcandidate"
    "integer pixelsamples" [320]

Film "image"
    "integer xresolution" [200]
    "integer yresolution" [200]

WorldBegin

# AttributeBegin
#     CoordSysTransform "camera"
#     LightSource "distant"
#         "point from" [0 0 0]
#         "point to"   [0 0 1]
#         "rgb L"    [1 1 1]
# AttributeEnd

{worldAttributes}

WorldEnd
'''

balls = '''
# an orangish sphere
AttributeBegin
    Translate -2 0 0
    Material "matte" "color Kd" [0.0 0.1 0.8]
    Shape "sphere" "float radius" [1]
AttributeEnd

# an orangish sphere
AttributeBegin
    Translate 2 0 0
    Material "matte" "color Kd" [1 0.0 0.1]
    Shape "sphere" "float radius" [1]
AttributeEnd
'''



meshTemplate = '''AttributeBegin
    ConcatTransform [
{transform}
    ]

    {materialString}

    Include "{geoFilePath}"
AttributeEnd

'''

geoTemplate = '''
Shape "trianglemesh"
        "integer indices" [{indices}]
        "point P" [
{points}
        ]
{normalString}
'''


lightTemplate = '''AttributeBegin
    ConcatTransform [
{transform}
    ]

    {lightText}

AttributeEnd

'''

normalTemplate = '''
        "normal N" [
{normals}
        ]'''
#         "float uv" [
# {UVs}
#         ]

commentTemplate = '# {comment}\n'

areaLightTemplate = '''
    AreaLightSource "diffuse" "rgb L" [ {0} ]

    Shape "trianglemesh"
        "integer indices" [0 1 2 2 1 3]
        "point P" [
            -0.5 0.5    0.0
            0.5  0.5    0.0
            -0.5 -0.5   0.0
            0.5  -0.5   0.0
        ]
'''

damascusTextureTemplate = '''
    Texture "damascusTexture"
        "spectrum" "damascus"
        "float hammerStrength"  {0}
        "float hammerFrequency" {1}
        "float layerThickness"  {2}

    Material "uber"
        "texture Kd" "damascusTexture"
        "rgb Ks" [.6 .6 .6]
        "rgb Kr" [.5 .5 .5]

'''

nerdTextureTemplate = '''
    MakeNamedMaterial "nerdMatte"
        "string type" "matte"
        "rgb Kd" [.3 .7 .3]


    MakeNamedMaterial "nerdPlastic"
        "string type" "plastic"
        "rgb Kd" [.1 .4 .1]
        "float roughness" [0.2]

    MakeNamedMaterial "nerdMetal"
        "string type" "metal"
        "rgb eta" [1.0 1.0 1.0]
        "rgb k" [.2 .9 .2]
        "float roughness" 0.3

    MakeNamedMaterial "nerdMix"
        "string type" "mix"
        # "float amount" [0.1]
        "string namedmaterial1" "nerdMatte"
        "string namedmaterial2" "nerdMetal"

    # NamedMaterial "nerdMatte"
    # NamedMaterial "nerdPlastic"
    # NamedMaterial "nerdMetal"
    NamedMaterial "nerdMix"

'''



def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)

def getLightIntensity(light):
    return (light.getColor()*light.getIntensity())[:-1]


def exportPbrt(filePath):
    assert filePath.endswith('.pbrt')

    # directory for geometry for this scene
    geoDirName = os.path.basename(sceneName()) + '.pbrt.d'
    geoDirPath = os.path.dirname(filePath) + '/' + geoDirName
    if not os.path.exists(geoDirPath): os.mkdir(geoDirPath)
    for p in glob.glob(geoDirPath + '/*'): os.remove(p)

    # camera
    # by default we use the editors perspective view
    camera = nt.Camera(u'perspShape')
    camTransform = camera.getParent()
    camPos = camTransform.getTranslation()
    camTransformString = stringContents2D(camTransform.getTransformation())
    camTransformString = stringContents2D(camTransform.getTransformation().asRotateMatrix())
    camLookAt = camera.getCenterOfInterestPoint('world')

    worldAttributes = ''


    # lights
    for light in ls(lights=True):
        if isinstance(light, nodetypes.PointLight):
            lightText = 'LightSource "point" "rgb I" [{0}]'.format(
                stringContents(getLightIntensity(light)),
            )
        elif isinstance(light, nodetypes.DirectionalLight):
            lightText = 'LightSource "distant" "rgb L" [{0}] "point to" [0 0 -1]'.format(
                stringContents(getLightIntensity(light)),
            )
        elif isinstance(light, nodetypes.SpotLight):
            lightText = 'LightSource "spot" "rgb I" [{0}] "point to" [0 0 -1] "float coneangle" [{1}] "float conedeltaangle" [{2}]'.format(
                stringContents(getLightIntensity(light)),
                light.getConeAngle(),
                light.getPenumbra(),
            )
        elif isinstance(light, nodetypes.AreaLight):
            lightText = areaLightTemplate.format(
                stringContents(getLightIntensity(light))
            )
        else:
            print "Unknown light type: " + str(light)
            continue

        worldAttributes += commentTemplate.format(comment=light.nodeName())
        worldAttributes += lightTemplate.format(
            transform=indent(stringContents2D(light.getParent().getTransformation()), 2),
            lightText=lightText,
        )

    # meshes
    for mesh in ls(type='mesh'):
        trianglesPerPoly, vertexIndices = mesh.getTriangles()

        trianglePointCounts, pointIndicies   = mesh.getVertices()


        if slowNormals:
            points  = mesh.getPoints()
            verts = []
            normals = []
            for triangleVertexIndecies in grouper(3, vertexIndices):  # for each triangle
                faceSets = ( { face.index() for face in mesh.verts[i].connectedFaces() } for i in triangleVertexIndecies )
                faceIndex = reduce(lambda a,b: a.intersection(b), faceSets).pop()
                for vertexIndex in triangleVertexIndecies:
                    verts.append(points[vertexIndex])
                    normals.append(mesh.getFaceVertexNormal(faceIndex, vertexIndex, space='preTransform'))

            indices = xrange(len(normals))
            normalString = normalTemplate.format(normals =indent(stringContents2D(normals), 3))
        else:
            verts = mesh.getPoints()
            indices = vertexIndices
            normalString = ''

        # print getClosestNorma
        # print len(points)
        # print len(indices)
        # print len(normals)
        # print len(verts)

        # material
        materialString = ''
        # try:
        shadingGroups = mesh.shadingGroups()
        if shadingGroups:
            lamberts = filter(lambda x: isinstance(x,nt.Lambert), shadingGroups[0].inputs())
            if lamberts:
                lambert = lamberts[0]

                # check for pbrt-texture inputs
                pbrtTextures = filter(lambda x: 'PbrtTextureNode' in str(x.type()), lambert.inputs())
                if pbrtTextures:
                    pbrtTexture = pbrtTextures[0]
                    materialString = damascusTextureTemplate.format(
                        # pbrtTexture.attr(pbrtTexture.hammerStrength  ),
                        # pbrtTexture.attr(pbrtTexture.hammerFrequency ),
                        # pbrtTexture.attr(pbrtTexture.layerThickness  )
                        pbrtTexture.attr('attrib_hammerStrength').get(),
                        pbrtTexture.attr('attrib_hammerFrequency').get(),
                        pbrtTexture.attr('attrib_layerThickness').get()
                    )
                else:
                    materialString = 'Material "matte" "rgb Kd" [ {0} ]'.format(
                        stringContents(lambert.getColor()[:-1])
                    )


        # except:
        #     print 'bad color'


        geoFileName = base64.b64encode(mesh.nodeName()) + '.pbrt'
        geoFilePath = geoDirPath + '/' + geoFileName

        geoAttributes = geoTemplate.format(
            indices =stringContents(indices),
            points  =indent(stringContents2D(verts),   3),
            normalString=normalString,
            # UVs     =indent(stringContents2D(zip(*UVs)), 3),
        )

        with open(geoFilePath, 'w') as geoFile:
            geoFile.write(commentTemplate.format(comment=mesh.nodeName()))
            geoFile.write(geoAttributes)

        # indices[1::3], indices[2::3] = indices[2::3], indices[1::3]
        worldAttributes += commentTemplate.format(comment=mesh.nodeName())
        worldAttributes += meshTemplate.format(
            transform=indent(stringContents2D(mesh.getParent().getTransformation()), 2),
            materialString=materialString,
            geoFilePath=geoDirName + '/' + geoFileName
        )
    # worldAttributes = balls







    # metaballs
    for metaball in ls(type='CandyBox'):
        print 'processing metaball:', metaball.name()
        path_bloomy = '{}/candyBox_{}.bloomy'.format(        candyBox.path_baseBloomy, metaball.name())
        path_obj    = '{}/candyBox_{}_pbrtExport.obj'.format(candyBox.path_baseObj,    metaball.name())


        candyBox.makeBlobby.polygonize(
            path_bloomy,
            path_obj,
            polygonSpacing=0.05
            # polygonSpacing=0.5
        )

        with open(path_obj) as f:
            lines = f.readlines()
        vertices  = np.array([ map(float,                                                  line.split()[1:])  for line in lines if line.startswith('v ' )])
        normals   = np.array([ map(float,                                                  line.split()[1:])  for line in lines if line.startswith('vn ')])
        faces     = np.array([ [ map(lambda x: int(x)-1, corner.split('//')) for corner in line.split()[1:] ] for line in lines if line.startswith('f ' )])
        print 'len', len(vertices)


        print 'shape up'
        print normals.shape
        normalString = normalTemplate.format(normals=indent(stringContents2D(normals), 3))

        geoFileName = base64.b64encode(metaball.nodeName()) + '.pbrt'
        geoFilePath = geoDirPath + '/' + geoFileName

        geoAttributes = geoTemplate.format(
            indices =stringContents(faces[:,:,0].reshape((-1,))),  # first, take only the first indecies. then linearize
            points  =indent(stringContents2D(vertices),   3),
            normalString=normalString,
            # UVs     =indent(stringContents2D(zip(*UVs)), 3),
        )

        with open(geoFilePath, 'w') as geoFile:
            geoFile.write(commentTemplate.format(comment=metaball.nodeName()))
            geoFile.write(geoAttributes)

        # indices[1::3], indices[2::3] = indices[2::3], indices[1::3]
        worldAttributes += commentTemplate.format(comment=metaball.nodeName())
        worldAttributes += meshTemplate.format(
            transform=indent(stringContents2D(metaball.getParent().getTransformation()), 2),
            materialString=nerdTextureTemplate,
            geoFilePath=geoDirName + '/' + geoFileName
        )

    # compose
    pbrt = pbrtTemplate.format(
        # camTransform=indent(camTransformString, 1),
        # camTranslate=stringContents(camPos),
        camPos      =stringContents(camPos),
        camLookAt   =stringContents(camLookAt),
        camFov=camera.getHorizontalFieldOfView(),
        filename=os.path.basename(filePath),
        worldAttributes=worldAttributes,
    )
    # print pbrt

    with open(filePath, 'w') as f:
        f.write(pbrt)


# converts current scene to pbrt, renders it to exr, converts exr to png
def render():
    assert path_pbrtExecutable

    path_scene = sceneName()
    assert path_scene
    path_pbrtFile = os.path.abspath(path_scene     + '.pbrt' )
    path_exr      = os.path.abspath(path_pbrtFile  + '.exr'  )
    path_png      = os.path.abspath(path_exr       + '.png'  )
    print "making pbrt file:", path_pbrtFile
    exportPbrt(path_pbrtFile)
    # os.system('~/pbrt-v2-master/src/bin/pbrt --outfile "{0}" "{1}"'.format(path_exr, path_pbrtFile))

    print 'starting rendering'
    p = subprocess.Popen([
            # '{} --outfile "{}" "{}"'.format(path_pbrtExecutable, path_exr, path_pbrtFile)
            path_pbrtExecutable,
            '--outfile',
            path_exr,
            path_pbrtFile
        ],
        # stdout=sys.__stdout__,
        # stderr=sys.__stderr__,
        # shell=True  # bad security practice
    )

    p.communicate()
    print 'rendering finished'

    # print
    # print ' ====== begin pbrt output ====== '
    # out, err = p.communicate()
    # # print out
    # print err.replace("Error in ioctl() in TerminalWidth(): 25", "")
    # print ' ====== end pbrt output ====== '
    # print

    os.system('convert "{0}" "{1}"'.format(path_exr, path_png))  # convert .exr to .png

    return path_png


if __name__ == '__main__':
    openFile(mayaSceneFile)
    # exportPbrt("/u/students/domnom/408/scenes/cuube.pbrt")
    path_png = render()
    print 'done. \nOutput file:', path_png
    os.system('gnome-open "{0}"'.format(path_png))
