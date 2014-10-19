#!/bin/env python

# path shenanigans
import sys
import os.path as p  # not to be confused with sys.path
def addToPath( searchPath ) :
    if searchPath not in sys.path:
        sys.path.append( searchPath )
path_this = p.expanduser( '~/teamCandy/MayaToPbrt/' )
addToPath( path_this )


from pymel.core import *
import sys

import mayaToPbrt


frames = 5



def doRender( preview ):
    reload( mayaToPbrt )
    pngPath = mayaToPbrt.render()
    preview.setImage( pngPath )
    print 'done', pngPath


def doExportSequence( ):
    reload(mayaToPbrt)
    for frame in xrange( 1, frames + 1 ) :
        mayaToPbrt.exportSequence( frame )


win = None
def initializePlugin( mobject ):
    global win
    windowTitle = "Pbrt render"
    win = window(windowTitle, title = windowTitle )

    layout = columnLayout()
    preview = image(
        # image=sceneName()+'.pbrt.exr.png',
        width = 400,
        height = 400,
    )
    button(
        command = Callback( doRender, preview ),
        label = "Pbrt Render",
        width = 200,
        height = 100,
    )
    button(
        command = Callback( doExportSequence ),
        label = "Pbrt Export Sequence",
        width = 200,
        height = 100,
    )

    win.show()


# unload
def uninitializePlugin( mobject ):
    try:
        win.delete()
    except:
        pass
