import numpy as np
from scipy.spatial.transform import Rotation
from fury import actor, window
from fury.animation.timeline import Timeline
from fury.animation.interpolator import LinearInterpolator
from fury.gltf import glTF
from fury.data import fetch_gltf, read_viz_gltf

scene = window.Scene()

showm = window.ShowManager(scene,
                           size=(900, 768), reset_camera=False,
                           order_transparent=True)
showm.initialize()

fetch_gltf('BoxAnimated', 'glTF')
filename = read_viz_gltf('BoxAnimated')

gltf_obj = glTF(filename)
actors = gltf_obj.actors()
transforms = gltf_obj.node_transform
nodes = gltf_obj.nodes

print(len(actors))

main_timeline = Timeline(playback_panel=True)

for transform in transforms:
    target_node = transform['node']
    for i, node_list in enumerate(nodes):
        if target_node in node_list:
            print(i)
            timeline = Timeline(actors[i])

            timeframes = transform['input']
            transforms = transform['output']
            prop = transform['property']
            print(prop)

            for time, node_tran in zip(timeframes, transforms):
                
                if prop == 'rotation':
                    rot = Rotation.from_quat(node_tran)
                    rot_euler = rot.as_euler('xyz', degrees=True)
                    timeline.set_rotation(time[0], rot_euler)
                if prop == 'translation':
                    print('chaning position')
                    timeline.set_position(time[0], node_tran)

            timeline.set_position_interpolator(LinearInterpolator)
            timeline.set_rotation_interpolator(LinearInterpolator)
            main_timeline.add_timeline(timeline)
        else:
            main_timeline.add_static_actor(actors[i])


def timer_callback(_obj, _event):
    main_timeline.update_animation()
    showm.render()


# Adding the callback function that updates the animation
showm.add_timer_callback(True, 10, timer_callback)

showm.start()
