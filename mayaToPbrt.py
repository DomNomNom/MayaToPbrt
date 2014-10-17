
import os.path as p


###### config ######

pbrtExecutable = ''     # eg. '~/408/final/comp408-project3/bin/pbrt'
slowNormals = False

###### end config ######

assert pbrtExecutable
pbrtExecutable = p.expanduser(pbrtExecutable)


# basePath = p.expanduser('~/maya/2015-x64/plug-ins/MayaToPBRT-data')
# mayaSceneFile = basePath+'/cuube.ma'  # only needed in standalone



if __name__ == '__main__':
    print 'starting pymel...'  # A printout to say that we are starting

from pymel.core import *

import os
from itertools import product, izip_longest
import subprocess

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
Film "image"
    "integer xresolution" [576]
    "integer yresolution" [384]

WorldBegin

TransformBegin
	Rotate 90 0 0 1
	Rotate 90 0 1 0

	LightSource "infinite" 
		"color L" [0.100000 0.100000 0.100000]
		"integer nsamples" [100]
		"string mapname" ["CO332_26-05-2014_TeamCandy_2k.exr"]

TransformEnd

AttributeBegin
    CoordSysTransform "camera"
    LightSource "distant"
        "point from" [0 0 0]
        "point to"   [0 0 1]
        "rgb L"    [1 1 1]
AttributeEnd

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



meshTemplate = '''
AttributeBegin
    ConcatTransform [
{transform}
    ]

    {materialString}
    Shape "trianglemesh"
        "integer indices" [{indices}]
        "point P" [
{points}
        ]
{normalString}
AttributeEnd
'''



lightTemplate = '''
AttributeBegin
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


def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)

def getLightIntensity(light):
    return (light.getColor()*light.getIntensity())[:-1]


def exportPbrt(filePath):
    assert filePath.endswith('.pbrt')

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


        # indices[1::3], indices[2::3] = indices[2::3], indices[1::3]
        worldAttributes += meshTemplate.format(
            transform=indent(stringContents2D(mesh.getParent().getTransformation()), 2),
            materialString=materialString,
            indices =stringContents(indices),
            points  =indent(stringContents2D(verts),   3),
            normalString=normalString,
            # UVs     =indent(stringContents2D(zip(*UVs)), 3),
        )

    # worldAttributes = balls



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
    assert pbrtExecutable

    scenePath = sceneName()
    assert scenePath
    pbrtPath = os.path.abspath(scenePath + '.pbrt' )
    exrPath  = os.path.abspath(pbrtPath  + '.exr'  )
    pngPath  = os.path.abspath(exrPath   + '.png'  )
    print "making pbrt file:", pbrtPath
    exportPbrt(pbrtPath)
    # os.system('~/pbrt-v2-master/src/bin/pbrt --outfile "{0}" "{1}"'.format(exrPath, pbrtPath))

    p = subprocess.Popen([
            '{2} --outfile "{0}" "{1}"'.format(exrPath, pbrtPath, pbrtExecutable)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True  # bad security practice
    )

    print
    print ' ====== begin pbrt output ====== '
    out, err = p.communicate()
    # print out
    print err.replace("Error in ioctl() in TerminalWidth(): 25", "")
    print ' ====== end pbrt output ====== '
    print

    os.system('convert "{0}" "{1}"'.format(exrPath, pngPath))  # convert .exr to .png
    os.system('convert "{0}" "{1}"'.format(exrPath, pngPath))  # convert .exr to .png

    return pngPath


if __name__ == '__main__':
    openFile(mayaSceneFile)
    # exportPbrt("/u/students/domnom/408/scenes/cuube.pbrt")
    pngPath = render()
    print 'done. \nOutput file:', pngPath
    os.system('gnome-open "{0}"'.format(pngPath))
