#!/bin/env python

# path shenanigans
import sys
import os.path as p  # not to be confused with sys.path
def addToPath(searchPath):
    if searchPath not in sys.path:
        sys.path.append(searchPath)
path_this = p.expanduser('~/teamCandy/MayaToPbrt/')
addToPath(path_this)



libPath_maya = p.abspath(p.join(p.dirname(sys.executable), p.pardir, 'lib', 'python2.6'))
addToPath(libPath_maya)
addToPath('/usr/pkg/lib/python2.7/site-packages')  # numpy

import os
import pymel.core as pm
import maya.mel as mel
import maya.cmds as cmds
import numpy as np
from contextlib import contextmanager
import shutil

# reload makeBlobby
if 'makeBlobby' in sys.modules:
    import makeBlobby
    reload(makeBlobby)
else:
    import makeBlobby


# folders that we put stuff in
path_baseObj    = p.join(path_this, 'polygonizer', 'OBJs')
path_baseBloomy = p.join(path_this, 'polygonizer', 'bloomies')
def ensurePathExists(path):
    path = p.dirname(path)
    if not p.exists(path):
        os.makedirs(path)
ensurePathExists(path_baseObj)
ensurePathExists(path_baseBloomy)


# cudos to http://stackoverflow.com/questions/1969240/mapping-a-range-of-values-to-another because I'm lazy
def mapRange(value, leftMin, leftMax, rightMin, rightMax):
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)

# removes the a element from the tuple
def withoutElement(tup, indexOfElement):
    return tup[:indexOfElement] + tup[indexOfElement+1:]
def withoutElements(tup, *indecies):
    return reduce(  # functional programming FTW
        lambda tup, index: withoutElement(tup, indexOfElement),
        indecies,
        tup
    )

# Monitors a CandyBox for changes and updates the .obj and .bloomy only when necessary
class CandyManager(object):
    def __init__(self, candyBox):
        self.candyBox = candyBox
        self.firstTime = True
        self.index_polySpacing = 3
        self.index_seed = 5

    def getParams(self):
        self.candyBox.getAttr('sphericalness')

        return (
            self.candyBox.getAttr('sphericalness'),
            0.25,
            0.25 * (1.0 - self.candyBox.getAttr('variation')),
            mapRange(self.candyBox.getAttr('quality'), 0.0, 1.0, 0.40, 0.02),
            int(self.candyBox.getAttr('complexity')),
            int(self.candyBox.getAttr('seed'))
        )

    # returns true if a reload is required
    def update(self):
        if self.firstTime:
            self.oldParams = self.getParams()
            self.oldPath_bloomy = self.candyBox.path_bloomy
        self.newParams = self.getParams()

        newObjFile = self.oldPath_bloomy != self.candyBox.path_bloomy

        if self.firstTime or newObjFile or self.newParams != self.oldParams:
            pass
            if self.firstTime or newObjFile or (
                withoutElement(self.newParams, self.index_polySpacing) !=
                withoutElement(self.oldParams, self.index_polySpacing)
            ):
                print 'full chain'
                makeBlobby.makeBlob(  # TODO: refactor the API
                    self.candyBox.path_obj,
                    *self.newParams,
                    path_bloomy=self.candyBox.path_bloomy
                )
            else:
                print 'quality repolygonize'
                makeBlobby.polygonize(
                    self.candyBox.path_bloomy,
                    self.candyBox.path_obj,
                    polygonSpacing=self.newParams[self.index_polySpacing]
                )

            makeBlobby.centerObj(self.candyBox.path_obj)

            self.firstTime = False
            self.oldParams = self.newParams
            self.oldPath_bloomy = self.candyBox.path_bloomy
            return True

        return False



#######################################################

# the Locator node

import maya.OpenMaya as om
import maya.OpenMayaRender as OpenMayaRender
import maya.OpenMayaMPx as mpx
glRenderer = OpenMayaRender.MHardwareRenderer.theRenderer()
gl = glRenderer.glFunctionTable()



def createAttr(cls, attrName, dataType=om.MFnNumericData.kFloat, default=0.0, softMin=0.0, softMax=1.0):
    attribute = om.MFnNumericAttribute()
    short = attrName
    attr = attribute.create(attrName, short, dataType, default)
    if dataType in [om.MFnNumericData.kFloat, om.MFnNumericData.kLong]:
        attribute.setSoftMin(softMin)
        attribute.setSoftMax(softMax)
    attribute.setStorable(1)
    cls.addAttribute(attr)
    exec('cls.attribute_{} = attribute'.format(attrName))
    # cls.attributeAffects(attr, mpx.cvar.MPxDeformerNode_outputGeom)
    return attr



# yields a number of points around the circle
def circle(numPoints=24):
    for i in xrange(numPoints):
        theta = np.pi * 2 * i / float(numPoints)
        yield (np.cos(theta), np.sin(theta))

# manages opengl draw state
@contextmanager
def glDraw(drawType=OpenMayaRender.MGL_LINE_LOOP):
    gl.glBegin(drawType)
    yield
    gl.glEnd()

# imports a obj file into the scene
def importObj(objPath):
    # clean up our previous export
    pm.delete(filter(
        lambda x: 'bloomy' in x.name(),
        [ x.parent(0) for x in pm.ls(type='mesh') ]
    ))

    # load the OBJ
    # can't be bothered converting this to proper python
    mel.eval('file -import -type "OBJ"  -ignoreVersion -ra true -mergeNamespacesOnClash false -namespace "caandy" -options "mo=1"  -pr "{}";'.format(objPath))



class CandyBox(pm.api.plugins.LocatorNode): # Locatos

    @classmethod
    def initialize(cls):
        # createAttr(cls, 'BBQ', om.MFnNumericData.kFloat)
        createAttr(cls, 'sphericalness', default=0.666, softMin=-0.3,   softMax=1.0,)
        createAttr(cls, 'complexity',    default=7,   softMin=1,      softMax=20, dataType=om.MFnNumericData.kLong)
        createAttr(cls, 'variation',     default=0.2, softMin=0,      softMax=1,  )
        createAttr(cls, 'quality',       default=0.5, softMin=0,      softMax=1,  )
        createAttr(cls, 'seed',             dataType=om.MFnNumericData.kLong,    default=133)
        createAttr(cls, 'fullModel',        dataType=om.MFnNumericData.kBoolean, default=True)
        createAttr(cls, 'export',           dataType=om.MFnNumericData.kBoolean, default=False)
        print 'initialized CandyBox node type'


    def __init__(self, *args, **kwargs):
        super(CandyBox, self).__init__(*args, **kwargs)

        print 'creating instance of CandyBox'

        self.candyManager = CandyManager(self)
        self.locatorCenter = np.array([0.0, 0.0, 0.0])
        self.locatorScale  = np.array([1.0, 1.0, 1.0])
        self.path_prefix = 'candyBox_'

        def getAttr(attrName):
            return pm.getAttr('{}.{}'.format(self.name(), attrName))
        def setAttr(attrName, value):
            return pm.setAttr('{}.{}'.format(self.name(), attrName), value)

        def draw(view, path, style, status):
            self.path_obj    = '{}/{}{}.obj'.format(   path_baseObj,    self.path_prefix, self.name())
            self.path_bloomy = '{}/{}{}.bloomy'.format(path_baseBloomy, self.path_prefix, self.name())


            # if p.exists(self.path_obj):
            #     os.rename(self.path_obj, self.path_obj+'.old')

            # angle = getAttr('BBQ') # pm.getAttr('myCandyBox.BBQ')
            # print 'BBBBQ:', angle
            # print "bbq? ", om.MPlug(self, self.attribute_BBQ).asFloat()
            view.beginGL()
            if self.candyManager.update():
                # read the .obj file if neccesary
                with open(self.path_obj) as f:
                    objText = f.read().split('\n')
                self.vertices  = np.array([ map(float,                                                  line.split()[1:])  for line in objText if line.startswith('v ' )])
                self.normals   = np.array([ map(float,                                                  line.split()[1:])  for line in objText if line.startswith('vn ')])
                self.faces     = np.array([ [ map(lambda x: int(x)-1, corner.split('//')) for corner in line.split()[1:] ] for line in objText if line.startswith('f ' )])
                # importObj(self.path_obj)
                self.min = self.vertices.min(0)
                self.max = self.vertices.max(0)
                self.locatorCenter = (self.max + self.min) / 2
                self.locatorScale  = (self.max - self.min) / 2
                # print 'update'

                # importObj(self.path_obj)
                # pm.select(self.name())

            else:
                pass
                # print 'no update'

            # export
            if (getAttr('export')):

                def makeNerdPath(nerdNumber):
                    return '{}/{}nerd{:03d}.obj'.format(path_baseObj, self.path_prefix, nerdNumber)

                nerdNumber = 0
                path_export = makeNerdPath(nerdNumber)
                while p.exists(path_export):
                    nerdNumber += 1
                    path_export = makeNerdPath(nerdNumber)

                shutil.copy(self.path_obj, path_export)
                setAttr('export', False)
                print 'exported to', path_export.split('/')[-1]

            # draw the objecet
            if (getAttr('fullModel')):
                gl.glPolygonMode(OpenMayaRender.MGL_FRONT_AND_BACK, OpenMayaRender.MGL_LINE);
                # gl.glScalef(1.01, 1.01, 1.01)
                with glDraw(OpenMayaRender.MGL_TRIANGLES):
                    for indexes in self.faces:
                        vertexIndecies, normalIndecies = zip(*indexes)  # transpose
                        for corner in xrange(3):
                            gl.glNormal3f(*self.normals[  normalIndecies[corner]]);  # argument unpacking FTW
                            gl.glVertex3f(*self.vertices[vertexIndecies[corner]]);
                gl.glPolygonMode(OpenMayaRender.MGL_FRONT_AND_BACK, OpenMayaRender.MGL_FILL);

            else:


                gl.glTranslatef(*self.locatorCenter)
                gl.glScalef(*self.locatorScale)
                gl.glRotatef(45.0,  0, 0, 1);
                gl.glRotatef(45.0,  0, 1, 0);
                circleSegments = int(mapRange(self.getAttr('quality'), 0.0, 1.0, 8.0, 30.0))
                with glDraw():
                    for x,y in circle(circleSegments): gl.glVertex3f(0.0, x,   y  );
                with glDraw():
                    for x,y in circle(circleSegments): gl.glVertex3f(x,   0.0, y  );
                with glDraw():
                    for x,y in circle(circleSegments): gl.glVertex3f(x,   y,   0.0);
                view.endGL()


        # pbrt obj export


        # set the functions
        # this is a hack. why can't I just define them at the class level? :(
        self.draw = draw
        self.getAttr = getAttr
        print 'end of constructor'



# unload

def uninitializePlugin(mobject):
    CandyBox.deregister(mobject)


def initializePlugin(mobject):
    CandyBox.register(mobject)