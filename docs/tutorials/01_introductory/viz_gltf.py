"""
=======================
Visualizing a glTF file
=======================
In this tutorial, we will show how to display a glTF file in a scene.
"""

from fury import window
from fury.gltf import glTF
from fury.data import fetch_gltf, read_viz_gltf

##############################################################################
# Create a scene.

scene = window.Scene()
scene.SetBackground(0.1, 0.1, 0.4)

##############################################################################
# Retrieving the gltf model.
fetch_gltf('CesiumMan', 'glTF')
filename = read_viz_gltf('CesiumMan')

##############################################################################
# Initialize the glTF object and get actors using `actors` method.
# Note: You can always manually create actor from polydata, and apply texture
# or materials manually afterwards.
# Experimental: For smooth mesh/actor you can set `apply_normals=True`.

gltf_obj = glTF(filename)
actors = gltf_obj.actors()

##############################################################################
# Add all the actor from list of actors to the scene.

scene.add(*actors)

##############################################################################
# Applying camera

cameras = gltf_obj.cameras
# print(gltf_obj.node_transform)
if cameras:
    scene.SetActiveCamera(cameras[0])

interactive = True

if interactive:
    window.show(scene, size=(1280, 720))

window.record(scene, out_path='viz_gltf.png', size=(1280, 720))
