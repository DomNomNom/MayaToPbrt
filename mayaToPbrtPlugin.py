

###### config ######

mayaToPbrtLocation = '' # this folder. eg. '~/408/final/MayaToPbrt'
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

win = None
def initializePlugin(mobject):
    global win
    windowTitle = "Pbrt render"
    win = window(windowTitle, title=windowTitle)

    layout = columnLayout()
    preview = image(
        # image=sceneName()+'.pbrt.exr.png',
        width=200,
        height=200,
    )
    button(
        command=Callback(doRender, preview),
        label="Pbrt Render",
        width=200,
        height=100,
    )

    win.show()


# unload
def uninitializePlugin(mobject):
    try:
        win.delete()
    except:
        pass