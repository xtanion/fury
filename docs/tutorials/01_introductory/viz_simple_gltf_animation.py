from scipy.spatial.transform import Rotation
from fury import window
from fury.animation.timeline import Timeline
from fury.animation.interpolator import (LinearInterpolator, StepInterpolator,
                                         CubicSplineInterpolator)
from fury.gltf import glTF
from fury.data import fetch_gltf, read_viz_gltf

scene = window.Scene()

showm = window.ShowManager(scene,
                           size=(900, 768), reset_camera=False,
                           order_transparent=True)
showm.initialize()

fetch_gltf('InterpolationTest', 'glTF')
filename = read_viz_gltf('InterpolationTest')

gltf_obj = glTF(filename)
actors = gltf_obj.actors()

# simplyfy the example, add the followingcode to a function indide the glTF
# object.
transforms = gltf_obj.node_transform
nodes = gltf_obj.nodes

interpolator = {
    'LINEAR': LinearInterpolator,
    'STEP': StepInterpolator,
    'CUBICSPLINE': LinearInterpolator
}

main_timeline = Timeline(playback_panel=True)

for transform in transforms:
    target_node = transform['node']
    for i, node_list in enumerate(nodes):
        if target_node in node_list:
            timeline = Timeline()
            timeline.add_actor(actors[i])

            timeframes = transform['input']
            transforms = transform['output']
            prop = transform['property']
            interp = interpolator.get(transform['interpolation'])

            for time, node_tran in zip(timeframes, transforms):

                if prop == 'rotation':
                    rot = Rotation.from_quat(node_tran)
                    rot_euler = rot.as_euler('xyz', degrees=True)
                    # print(rot_euler)
                    timeline.set_rotation(time[0], rot_euler)
                if prop == 'translation':
                    timeline.set_position(time[0], node_tran)
                if prop == 'scale':
                    timeline.set_scale(time[0], node_tran)

            timeline.set_position_interpolator(interp)
            timeline.set_rotation_interpolator(interp)
            timeline.set_scale_interpolator(interp)
            main_timeline.add_timeline(timeline)
        else:
            main_timeline.add_static_actor(actors[i])

scene.add(main_timeline)


def timer_callback(_obj, _event):
    main_timeline.update_animation()
    showm.render()


# Adding the callback function that updates the animation
showm.add_timer_callback(True, 10, timer_callback)

showm.start()
