import numpy as np
from fury import window
from fury.animation.timeline import Timeline
from fury.animation.interpolator import (LinearInterpolator, StepInterpolator,
                                         Slerp, Interpolator)
from fury.gltf import glTF
from fury.data import fetch_gltf, read_viz_gltf

scene = window.Scene()

showm = window.ShowManager(scene,
                           size=(900, 768), reset_camera=False,
                           order_transparent=True)
showm.initialize()


class TanCubicSplineInterpolator(Interpolator):
    def __init__(self, keyframes):
        super(TanCubicSplineInterpolator, self).__init__(keyframes)
        for time in self.keyframes:
            data = self.keyframes.get(time)
            value = data.get('value')
            if data.get('in_tangent') is None:
                data['in_tangent'] = np.zeros_like(value)
            if data.get('in_tangent') is None:
                data['in_tangent'] = np.zeros_like(value)

    def interpolate(self, t):
        t0, t1 = self.get_neighbour_timestamps(t)

        dt = self.get_time_tau(t, t0, t1)

        time_delta = t1 - t0
        p0 = self.keyframes.get(t0).get('value')
        tan_0 = self.keyframes.get(t0).get('out_tangent') * time_delta
        p1 = self.keyframes.get(t1).get('value')
        tan_1 = self.keyframes.get(t1).get('in_tangent') * time_delta
        # cubic spline equation using tangents
        t2 = dt * dt
        t3 = t2 * dt
        return (2 * t3 - 3 * t2 + 1) * p0 + (t3 - 2 * t2 + dt) * tan_0 + (
                -2 * t3 + 3 * t2) * p1 + (t3 - t2) * tan_1

fetch_gltf('InterpolationTest', 'glTF')
filename = read_viz_gltf('InterpolationTest')

gltf_obj = glTF(filename)
actors = gltf_obj.actors()

print(len(actors))

# simplyfy the example, add the followingcode to a function indide the glTF
# object.
transforms = gltf_obj.node_transform
nodes = gltf_obj.nodes

print(nodes)

interpolator = {
    'LINEAR': LinearInterpolator,
    'STEP': StepInterpolator,
    'CUBICSPLINE': TanCubicSplineInterpolator
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
            timeshape = timeframes.shape
            transhape = transforms.shape
            if transform['interpolation'] == 'CUBICSPLINE':
                transforms = transforms.reshape((timeshape[0], -1, transhape[1]))

            for time, node_tran in zip(timeframes, transforms):

                in_tan, out_tan = None, None
                if node_tran.ndim == 2:
                    cubicspline = node_tran
                    in_tan = cubicspline[0]
                    node_tran = cubicspline[1]
                    out_tan = cubicspline[2]

                if prop == 'rotation':
                    timeline.set_rotation(time[0], node_tran,
                                          in_tangent=in_tan,
                                          out_tangent=out_tan)

                    timeline.set_rotation_interpolator(interp)
                if prop == 'translation':
                    timeline.set_position(time[0], node_tran,
                                          in_tangent=in_tan,
                                          out_tangent=out_tan)

                    timeline.set_position_interpolator(interp)
                if prop == 'scale':
                    timeline.set_scale(time[0], node_tran,
                                       in_tangent=in_tan,
                                       out_tangent=out_tan)
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
