

###### config ######

mayaToPbrtLocation = '' # this folder. eg. '~/408/final/MayaToPbrt'
frames = 5 #23.976fps
assert mayaToPbrtLocation

###### end config ######




from pymel.core import *
import sys

import os.path as p
mayaToPbrtLocation = p.expanduser(mayaToPbrtLocation)
sys.path.append(mayaToPbrtLocation)  # where mayaToPbrt is
import mayaToPbrt


def doRender(preview):
    reload(mayaToPbrt)
    pngPath = mayaToPbrt.render()
    preview.setImage(pngPath)
    print 'done', pngPath

def doRenderSequence(preview):
    reload(mayaToPbrt)
    for frame in xrange( 0, frames ) :
        mayaToPbrt.renderSequence( frame, preview = False)

win = None
def initializePlugin(mobject):
    global win
    windowTitle = "Pbrt render"
    win = window(windowTitle, title=windowTitle)

    layout = columnLayout()
    preview = image(
        # image=sceneName()+'.pbrt.exr.png',
        width=400,
        height=600,
    )
    button(
        command=Callback(doRender, preview),
        label="Pbrt Render",
        width=400,
        height=100,
    )
    button(
        command=Callback(doRenderSequence, preview),
        label="Pbrt Render Sequence",
        width=400,
        height=100,
    )

    win.show()


# unload
def uninitializePlugin(mobject):
    try:
        win.delete()
    except:
        pass
