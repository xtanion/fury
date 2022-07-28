import time
import warnings

import numpy as np
from scipy.spatial import transform
from fury import utils, actor
from fury.actor import Container
from fury.animation.interpolator import LinearInterpolator, SplineInterpolator
from fury.ui.elements import PlaybackPanel
from fury.lib import Actor


class Timeline(Container):
    """Keyframe animation timeline class.

    This timeline is responsible for keyframe animations for a single or a
    group of models.
    It's used to handle multiple attributes and properties of Fury actors such
    as transformations, color, and scale.
    It also accepts custom data and interpolates them, such as temperature.
    Linear interpolation is used by default to interpolate data between the
    main keyframes.
    """

    def __init__(self, actors=None, playback_panel=False, length=None,
                 motion_path_res=0):

        super().__init__()
        self._data = {
            'keyframes': {
                'attribs': {},
                'camera': {}
            },
            'interpolators': {
                'attribs': {},
                'camera': {}
            }
        }
        self.playback_panel = None
        self._last_timestamp = 0
        self._current_timestamp = 0
        self._speed = 1
        self._timelines = []
        self._static_actors = []
        self._camera = None
        self._scene = None
        self._last_started_time = 0
        self._playing = False
        self._length = length
        self._final_timestamp = 0
        self._needs_update = False
        self._reverse_playing = False
        self._loop = False
        self._added_to_scene = True
        self._add_to_scene_time = 0
        self._remove_from_scene_time = None
        self._is_camera_animated = False
        self.motion_path_res = motion_path_res
        self._motion_path_actor = None

        # Handle actors while constructing the timeline.
        if playback_panel:
            def set_loop(loop):
                self._loop = loop

            def set_speed(speed):
                self.speed = speed

            self.playback_panel = PlaybackPanel()
            self.playback_panel.on_play = self.play
            self.playback_panel.on_stop = self.stop
            self.playback_panel.on_pause = self.pause
            self.playback_panel.on_loop_toggle = set_loop
            self.playback_panel.on_progress_bar_changed = self.seek
            self.playback_panel.on_speed_changed = set_speed
            self.add_actor(self.playback_panel, static=True)

        if actors is not None:
            self.add_actor(actors)

    def update_final_timestamp(self):
        """Calculates and returns the final timestamp of all keyframes.

        Returns
        -------
        float
            final timestamp that can be reached inside the Timeline.
        """
        if self._length is None:
            self._final_timestamp = max(self.final_timestamp,
                                        max([0] + [tl.update_final_timestamp()
                                                   for tl in self.timelines]))
        else:
            self._final_timestamp = self._length
        if self.has_playback_panel:
            self.playback_panel.final_time = self._final_timestamp
        return self._final_timestamp

    def update_motion_path(self, res=None):
        if res is None:
            res = self.motion_path_res
        lines = []
        colors = []
        if self.is_interpolatable('position'):
            ts = np.linspace(0, self.final_timestamp, res)
            [lines.append(self.get_position(t).tolist()) for t in ts]
            if self.is_interpolatable('color'):
                [colors.append(self.get_color(t)) for t in ts]
            elif len(self.items) == 1:
                colors = sum([i.vcolors[0] / 255 for i in self.items]) / \
                         len(self.items)
            else:
                colors = [1, 1, 1]
        if len(lines) > 0:
            lines = np.array([lines])
            if colors is []:
                colors = np.array([colors])

            mpa = actor.line(lines, colors=colors, opacity=0.6)
            if self._scene:
                # remove old motion path actor
                if self._motion_path_actor is not None:
                    self._scene.rm(self._motion_path_actor)
                self._scene.add(mpa)
            self._motion_path_actor = mpa
        [tl.update_motion_path(res) for tl in self.timelines]

    def set_timestamp(self, timestamp):
        """Set the current timestamp of the animation.

        Parameters
        ----------
        timestamp: float
            Current timestamp to be set.
        """
        if self.playing:
            self._last_started_time = \
                time.perf_counter() - timestamp / self.speed
        else:
            self._last_timestamp = timestamp

    def set_keyframe(self, attrib, timestamp, value, pre_cp=None,
                     post_cp=None, is_camera=False):
        """Set a keyframe for a certain attribute.

        Parameters
        ----------
        attrib: str
            The name of the attribute.
        timestamp: float
            Timestamp of the keyframe.
        value: ndarray
            Value of the keyframe at the given timestamp.
        is_camera: bool
            Indicated whether setting a camera property or general property.
        pre_cp: ndarray, shape (1, M), optional
            The control point in case of using `cubic Bézier interpolator` when
            time exceeds this timestamp.
        post_cp: ndarray, shape (1, M), optional
            The control point in case of using `cubic Bézier interpolator` when
            time precedes this timestamp.
        """
        typ = 'attribs'
        if is_camera:
            typ = 'camera'
            self._is_camera_animated = True

        keyframes = self._data.get('keyframes')
        if attrib not in keyframes.get(typ):
            keyframes.get(typ)[attrib] = {}
        attrib_keyframes = self._data.get('keyframes').get(typ).get(attrib)
        attrib_keyframes[timestamp] = {
            'value': np.array(value).astype(np.float),
            'pre_cp': pre_cp,
            'post_cp': post_cp
        }
        interpolators = self._data.get('interpolators')
        if attrib not in interpolators.get(typ):
            interpolators.get(typ)[attrib] = \
                LinearInterpolator(attrib_keyframes)

        else:
            interpolators.get(typ).get(attrib).setup()

        if timestamp > self.final_timestamp:
            self._final_timestamp = timestamp
            if self.has_playback_panel:
                final_t = self.update_final_timestamp()
                self.playback_panel.final_time = final_t

        if timestamp > 0:
            self.update_animation(force=True)
        self.update_motion_path()

    def set_keyframes(self, attrib, keyframes, is_camera=False):
        """Set multiple keyframes for a certain attribute.

        Parameters
        ----------
        attrib: str
            The name of the attribute.
        keyframes: dict
            A dict object containing keyframes to be set.
        is_camera: bool
            Indicated whether setting a camera property or general property.

        Notes
        ---------
        Cubic Bézier curve control points are not supported yet in this setter.

        Examples
        ---------
        >>> pos_keyframes = {1: np.array([1, 2, 3]), 3: np.array([5, 5, 5])}
        >>> Timeline.set_keyframes('position', pos_keyframes)
        """
        for t in keyframes:
            keyframe = keyframes.get(t)
            self.set_keyframe(attrib, t, keyframe, is_camera=is_camera)

    def set_camera_keyframe(self, attrib, timestamp, value, pre_cp=None,
                            post_cp=None):
        """Set a keyframe for a camera property

        Parameters
        ----------
        attrib: str
            The name of the attribute.
        timestamp: float
            Timestamp of the keyframe.
        value: float
            Value of the keyframe at the given timestamp.
        pre_cp: float
            The control point in case of using `cubic Bézier interpolator` when
            time exceeds this timestamp.
        post_cp: float
            The control point in case of using `cubic Bézier interpolator` when
            time precedes this timestamp.
        """
        self.set_keyframe(attrib, timestamp, value, pre_cp, post_cp, True)

    def is_inside_scene_at(self, timestamp):
        if self._remove_from_scene_time is not None and \
                timestamp >= self._remove_from_scene_time:
            return False
        elif timestamp >= self._add_to_scene_time:
            return True
        return False

    def add_to_scene_at(self, timestamp):
        """Set timestamp for adding Timeline to scene event.

        Parameters
        ----------
        timestamp: float
            Timestamp of the event.
        """
        self._add_to_scene_time = timestamp

    def remove_from_scene_at(self, timestamp):
        """Set timestamp for removing Timeline to scene event.

        Parameters
        ----------
        timestamp: float
            Timestamp of the event.
        """
        self._remove_from_scene_time = timestamp

    def handle_scene_event(self, in_scene):
        if self._scene is not None:
            if in_scene and not self._added_to_scene:
                super(Timeline, self).add_to_scene(self._scene)
                self._added_to_scene = True
            elif not in_scene and self._added_to_scene:
                super(Timeline, self).remove_from_scene(self._scene)
                self._added_to_scene = False

    def set_camera_keyframes(self, attrib, keyframes):
        """Set multiple keyframes for a certain camera property

        Parameters
        ----------
        attrib: str
            The name of the property.
        keyframes: dict
            A dict object containing keyframes to be set.

        Notes
        ---------
        Cubic Bézier curve control points are not supported yet in this setter.

        Examples
        ---------
        >>> cam_pos = {1: np.array([1, 2, 3]), 3: np.array([5, 5, 5])}
        >>> Timeline.set_camera_keyframes('position', cam_pos)
        """
        self.set_keyframes(attrib, keyframes, is_camera=True)

    def set_interpolator(self, attrib, interpolator, is_camera=False,
                         spline_degree=None):
        """Set keyframes interpolator for a certain property

        Parameters
        ----------
        attrib: str
            The name of the property.
        interpolator: class
            The interpolator to be used to interpolate keyframes.
        is_camera: bool, optional
            Indicated whether dealing with a camera property or general
            property.
        spline_degree: int, optional
            The degree of the spline in case of setting a spline interpolator.

        Examples
        ---------
        >>> Timeline.set_interpolator('position', LinearInterpolator)
        """
        typ = 'attribs'
        if is_camera:
            typ = 'camera'
        if attrib in self._data.get('keyframes').get(typ):
            keyframes = self._data.get('keyframes').get(typ).get(attrib)
            if spline_degree is not None and interpolator is SplineInterpolator:
                interp = interpolator(keyframes, spline_degree)
            else:
                interp = interpolator(keyframes)
            self._data.get('interpolators').get(typ)[attrib] = interp

    def is_interpolatable(self, attrib, is_camera=False):
        """Checks whether a property is interpolatable.

        Parameters
        ----------
        attrib: str
            The name of the property.
        is_camera: bool
            Indicated whether checking a camera property or general property.

        Returns
        -------
        bool
            True if the property is interpolatable by the Timeline.

        Notes
        -------
        True means that it's safe to use `Interpolator.interpolate(t)` for the
        specified property. And False means the opposite.

        """
        typ = 'camera' if is_camera else 'attribs'
        return attrib in self._data.get('interpolators').get(typ)

    def set_camera_interpolator(self, attrib, interpolator):
        """Set the interpolator for a specific camera property.

        Parameters
        ----------
        attrib: str
            The name of the camera property.
            The already handled properties are position, focal, and view_up.

        interpolator: class
            The interpolator that handles the camera property interpolation
            between keyframes.

        Examples
        ---------
        >>> Timeline.set_camera_interpolator('focal', LinearInterpolator)
        """
        self.set_interpolator(attrib, interpolator, is_camera=True)

    def set_position_interpolator(self, interpolator, spline_degree=None):
        """Set the position interpolator for all actors inside the
        timeline.

        Parameters
        ----------
        interpolator: class
            The interpolator that would handle the position keyframes.

        spline_degree: int
            The degree of the spline interpolation in case of setting
            the `SplineInterpolator`.

        Examples
        ---------
        >>> Timeline.set_position_interpolator(SplineInterpolator, 5)
        """
        self.set_interpolator('position', interpolator,
                              spline_degree=spline_degree)

    def set_scale_interpolator(self, interpolator):
        """Set the scale interpolator for all the actors inside the
        timeline.

        Parameters
        ----------
        interpolator: class
            TThe interpolator that would handle the scale keyframes.

        Examples
        ---------
        >>> Timeline.set_scale_interpolator(StepInterpolator)
        """
        self.set_interpolator('scale', interpolator)

    def set_rotation_interpolator(self, interpolator):
        """Set the scale interpolator for all the actors inside the
        timeline.

        Parameters
        ----------
        interpolator: class
            The interpolator that would handle the rotation (orientation)
            keyframes.

        Examples
        ---------
        >>> Timeline.set_rotation_interpolator(Slerp)
        """
        self.set_interpolator('rotation', interpolator)

    def set_color_interpolator(self, interpolator):
        """Set the color interpolator for all the actors inside the
        timeline.

        Parameters
        ----------
        interpolator: class
            The interpolator that would handle the color keyframes.

        Examples
        ---------
        >>> Timeline.set_color_interpolator(LABInterpolator)
        """
        self.set_interpolator('color', interpolator)

    def set_opacity_interpolator(self, interpolator):
        """Set the opacity interpolator for all the actors inside the
        timeline.

        Parameters
        ----------
        interpolator: class
            The interpolator that would handle the opacity keyframes.

        Examples
        ---------
        >>> Timeline.set_opacity_interpolator(StepInterpolator)
        """
        self.set_interpolator('opacity', interpolator)

    def set_camera_position_interpolator(self, interpolator):
        """Set the camera position interpolator.

        Parameters
        ----------
        interpolator: class
            The interpolator that would handle the interpolation of the camera
            position keyframes.
        """
        self.set_camera_interpolator("position", interpolator)

    def set_camera_focal_interpolator(self, interpolator):
        """Set the camera focal position interpolator.

        Parameters
        ----------
        interpolator: class
            The interpolator that would handle the interpolation of the camera
            focal position keyframes.
        """
        self.set_camera_interpolator("focal", interpolator)

    def get_value(self, attrib, timestamp):
        """Returns the value of an attribute at any given timestamp.

        Parameters
        ----------
        attrib: str
            The attribute name.
        timestamp: float
            The timestamp to interpolate at.
        """
        return self._data.get('interpolators').get('attribs').get(
            attrib).interpolate(timestamp)

    def get_camera_value(self, attrib, timestamp):
        """Returns the value of an attribute interpolated at any given
        timestamp.

        Parameters
        ----------
        attrib: str
            The attribute name.
        timestamp: float
            The timestamp to interpolate at.

        """
        return self._data.get('interpolators').get('camera').get(
            attrib).interpolate(timestamp)

    def set_position(self, timestamp, position, pre_cp=None, post_cp=None):
        """Set a position keyframe at a specific timestamp.

        Parameters
        ----------
        timestamp: float
            Timestamp of the keyframe
        position: ndarray, shape (1, 3)
            Position value
        pre_cp: ndarray, shape (1, 3), optional
            The pre control point for the given position.
        post_cp: ndarray, shape (1, 3), optional
            The post control point for the given position.

        Notes
        -----
        `pre_cp` and `post_cp` only needed when using the cubic bezier
        interpolation method.
        """
        self.set_keyframe('position', timestamp, position, pre_cp, post_cp)

    def set_position_keyframes(self, keyframes):
        """Set a dict of position keyframes at once.
        Should be in the following form:
        {timestamp_1: position_1, timestamp_2: position_2}

        Parameters
        ----------
        keyframes: dict(float: ndarray, shape(1, 3))
            A dict with timestamps as keys and positions as values.

        Examples
        --------
        >>> pos_keyframes = {1, np.array([0, 0, 0]), 3, np.array([50, 6, 6])}
        >>> Timeline.set_position_keyframes(pos_keyframes)
        """
        self.set_keyframes('position', keyframes)

    def set_rotation(self, timestamp, rotation, ):
        """Set a rotation keyframe at a specific timestamp.

        Parameters
        ----------
        timestamp: float
            Timestamp of the keyframe
        rotation: ndarray, shape(1, 3) or shape(1, 4)
            Rotation data in euler degrees with shape(1, 3) or in quaternions
            with shape(1, 4).
        """
        no_components = len(np.array(rotation).flatten())
        if no_components == 4:
            self.set_keyframe('rotation', timestamp, rotation)
        elif no_components == 3:
            # user is expected to set rotation order by default as setting
            # orientation of a `vtkActor` z->x->y.
            rotation = transform.Rotation.from_euler('zxy',
                                                     rotation[[2, 0, 1]],
                                                     degrees=True).as_quat()
            self.set_keyframe('rotation', timestamp, rotation)
        else:
            warnings.warn(f'Keyframe with {no_components} components is not a '
                          f'valid rotation data. Skipped!')

    def set_rotation_as_vector(self, timestamp, vector):
        """Set a rotation keyframe at a specific timestamp.

        Parameters
        ----------
        timestamp: float
            Timestamp of the keyframe
        vector: ndarray, shape(1, 3)
            Directional vector that describes the rotation.
        """
        euler = transform.Rotation.from_rotvec(vector).as_euler('xyz', True)
        self.set_keyframe('rotation', timestamp, euler)

    def set_scale(self, timestamp, scalar):
        """Set a scale keyframe at a specific timestamp.

        Parameters
        ----------
        scalar
        timestamp: float
            Timestamp of the keyframe
        scalar: ndarray, shape(1, 3)
            Scale keyframe value associated with the timestamp.
        """
        self.set_keyframe('scale', timestamp, scalar)

    def set_scale_keyframes(self, keyframes):
        """Set a dict of scale keyframes at once.
        Should be in the following form:
        {timestamp_1: scale_1, timestamp_2: scale_2}

        Parameters
        ----------
        keyframes: dict(float: ndarray, shape(1, 3))
            A dict with timestamps as keys and scales as values.

        Examples
        --------
        >>> scale_keyframes = {1, np.array([1, 1, 1]), 3, np.array([2, 2, 3])}
        >>> Timeline.set_scale_keyframes(scale_keyframes)
        """
        self.set_keyframes('scale', keyframes)

    def set_color(self, timestamp, color):
        self.set_keyframe('color', timestamp, color)

    def set_color_keyframes(self, keyframes):
        """Set a dict of color keyframes at once.
        Should be in the following form:
        {timestamp_1: color_1, timestamp_2: color_2}

        Parameters
        ----------
        keyframes: dict
            A dict with timestamps as keys and color as values.

        Examples
        --------
        >>> color_keyframes = {1, np.array([1, 0, 1]), 3, np.array([0, 0, 1])}
        >>> Timeline.set_color_keyframes(color_keyframes)
        """
        self.set_keyframes('color', keyframes)

    def set_opacity(self, timestamp, opacity):
        """Value from 0 to 1"""
        self.set_keyframe('opacity', timestamp, opacity)

    def set_opacity_keyframes(self, keyframes):
        """Set a dict of opacity keyframes at once.
        Should be in the following form:
        {timestamp_1: opacity_1, timestamp_2: opacity_2}

        Parameters
        ----------
        keyframes: dict(float: ndarray, shape(1, 1) or float or int)
            A dict with timestamps as keys and opacities as values.

        Notes
        -----
        Opacity values should be between 0 and 1.

        Examples
        --------
        >>> opacity = {1, np.array([1, 1, 1]), 3, np.array([2, 2, 3])}
        >>> Timeline.set_scale_keyframes(opacity)
        """
        self.set_keyframes('opacity', keyframes)

    def get_position(self, t):
        """Returns the interpolated position.

        Parameters
        ----------
        t: float
            The time to interpolate position at.

        Returns
        -------
        ndarray(1, 3):
            The interpolated position.
        """
        return self.get_value('position', t)

    def get_rotation(self, t):
        """Returns the interpolated rotation.

        Parameters
        ----------
        t: float
            the time to interpolate rotation at.

        Returns
        -------
        ndarray(1, 3):
            The interpolated rotation.
        """
        q = self.get_value('rotation', t)
        r = transform.Rotation.from_quat(q)
        degrees = r.as_euler('zxy', degrees=True)[[1, 2, 0]]
        return degrees

    def get_scale(self, t):
        """Returns the interpolated scale.

        Parameters
        ----------
        t: float
            The time to interpolate scale at.

        Returns
        -------
        ndarray(1, 3):
            The interpolated scale.
        """
        return self.get_value('scale', t)

    def get_color(self, t):
        """Returns the interpolated color.

        Parameters
        ----------
        t: float
            The time to interpolate color value at.

        Returns
        -------
        ndarray(1, 3):
            The interpolated color.
        """
        return self.get_value('color', t)

    def get_opacity(self, t):
        """Returns the opacity value.

        Parameters
        ----------
        t: float
            The time to interpolate opacity at.

        Returns
        -------
        ndarray(1, 1):
            The interpolated opacity.
        """
        return self.get_value('opacity', t)

    def set_camera_position(self, timestamp, position):
        """Sets the camera position keyframe.

        Parameters
        ----------
        timestamp: float
            The time to interpolate opacity at.
        position: ndarray, shape(1, 3)
            The camera position
        """
        self.set_camera_keyframe('position', timestamp, position)

    def set_camera_focal(self, timestamp, position):
        """Sets camera's focal position keyframe.

        Parameters
        ----------
        timestamp: float
            The time to interpolate opacity at.
        position: ndarray, shape(1, 3)
            The camera position
        """
        self.set_camera_keyframe('focal', timestamp, position)

    def set_camera_view_up(self, timestamp, direction):
        """Sets the camera view-up direction keyframe.

        Parameters
        ----------
        timestamp: float
            The time to interpolate at.
        direction: ndarray, shape(1, 3)
            The camera view-up direction
        """
        self.set_camera_keyframe('view_up', timestamp, direction)

    def set_camera_rotation(self, timestamp, euler):
        """Sets the camera rotation keyframe.

        Parameters
        ----------
        timestamp: float
            The time to interpolate at.
        euler: ndarray, shape(1, 3)
            The euler angles describing the camera rotation in degrees.
        """
        self.set_camera_keyframe('rotation', timestamp, euler)

    def set_camera_position_keyframes(self, keyframes):
        """Set a dict of camera position keyframes at once.
        Should be in the following form:
        {timestamp_1: position_1, timestamp_2: position_2}

        Parameters
        ----------
        keyframes: dict(float: ndarray, shape(1, 3))
            A dict with timestamps as keys and opacities as values.

        Examples
        --------
        >>> pos = {0, np.array([1, 1, 1]), 3, np.array([20, 0, 0])}
        >>> Timeline.set_camera_position_keyframes(pos)
        """
        self.set_camera_keyframes('position', keyframes)

    def set_camera_focal_keyframes(self, keyframes):
        """Set multiple camera focal position keyframes at once.
        Should be in the following form:
        {timestamp_1: focal_1, timestamp_2: focal_1, ...}

        Parameters
        ----------
        keyframes: dict(float: ndarray, shape(1, 3))
            A dict with timestamps as keys and camera focal positions as
            values.

        Examples
        --------
        >>> focal_pos = {0, np.array([1, 1, 1]), 3, np.array([20, 0, 0])}
        >>> Timeline.set_camera_focal_keyframes(focal_pos)
        """
        self.set_camera_keyframes('focal', keyframes)

    def set_camera_view_up_keyframes(self, keyframes):
        """Set multiple camera view up direction keyframes.
        Should be in the following form:
        {timestamp_1: view_up_1, timestamp_2: view_up_2, ...}

        Parameters
        ----------
        keyframes: dict(float: ndarray, shape(1, 3))
            A dict with timestamps as keys and camera view up vectors as
            values.

        Examples
        --------
        >>> view_ups = {0, np.array([1, 0, 0]), 3, np.array([0, 1, 0])}
        >>> Timeline.set_camera_view_up_keyframes(view_ups)
        """
        self.set_camera_keyframes('view_up', keyframes)

    def get_camera_position(self, t):
        """Returns the interpolated camera position.

        Parameters
        ----------
        t: float
            The time to interpolate camera position value at.

        Returns
        -------
        ndarray(1, 3):
            The interpolated camera position.

        Notes
        -----
        The returned position does not necessarily reflect the current camera
        position, but te expected one.
        """
        return self.get_camera_value('position', t)

    def get_camera_focal(self, t):
        """Returns the interpolated camera's focal position.

        Parameters
        ----------
        t: float
            The time to interpolate at.

        Returns
        -------
        ndarray(1, 3):
            The interpolated camera's focal position.

        Notes
        -----
        The returned focal position does not necessarily reflect the current
        camera's focal position, but the expected one.
        """
        return self.get_camera_value('focal', t)

    def get_camera_view_up(self, t):
        """Returns the interpolated camera's view-up directional vector.

        Parameters
        ----------
        t: float
            The time to interpolate at.

        Returns
        -------
        ndarray(1, 3):
            The interpolated camera view-up directional vector.

        Notes
        -----
        The returned focal position does not necessarily reflect the actual
        camera view up directional vector, but the expected one.
        """
        return self.get_camera_value('view_up', t)

    def get_camera_rotation(self, t):
        """Returns the interpolated rotation for the camera expressed
        in euler angles.

        Parameters
        ----------
        t: float
            The time to interpolate at.

        Returns
        -------
        ndarray(1, 3):
            The interpolated camera's rotation.

        Notes
        -----
        The returned focal position does not necessarily reflect the actual
        camera view up directional vector, but the expected one.
        """
        return self.get_camera_value('rotation', t)

    def add(self, item):
        """Adds an item to the Timeline.
        This item can be an actor, Timeline, list of actors, or a list of
        Timelines.

        Parameters
        ----------
        item: Timeline, vtkActor, list(Timeline), or list(vtkActor)
            Actor/s to be animated by the timeline.
        """
        if isinstance(item, list):
            for a in item:
                self.add(a)
            return
        elif isinstance(item, Actor):
            self.add_actor(item)
        elif isinstance(item, Timeline):
            self.add_timeline(item)
        else:
            raise ValueError(f"Object of type {type(item)} can't be added to "
                             f"the timeline.")

    def add_timeline(self, timeline):
        """Adds an actor or list of actors to the Timeline.

        Parameters
        ----------
        timeline: Timeline or list(Timeline)
            Actor/s to be animated by the timeline.
        """
        if isinstance(timeline, list):
            for a in timeline:
                self.add_timeline(a)
            return
        self._timelines.append(timeline)

    def add_actor(self, actor, static=False):
        """Adds an actor or list of actors to the Timeline.

        Parameters
        ----------
        actor: vtkActor or list(vtkActor)
            Actor/s to be animated by the timeline.
        static: bool
            Indicated whether the actor should be animated and controlled by
            the timeline or just a static actor that gets added to the scene
            along with the Timeline.
        """
        if isinstance(actor, list):
            for a in actor:
                self.add_actor(a, static=static)
        elif static:
            self._static_actors.append(actor)
        else:
            actor.vcolors = utils.colors_from_actor(actor)
            super(Timeline, self).add(actor)

    @property
    def actors(self):
        """Returns a list of actors.

        Returns
        -------
        list:
            List of actors controlled by the Timeline.
        """
        return self.items

    @property
    def timelines(self):
        """Returns a list of child Timelines.

        Returns
        -------
        list:
            List of child Timelines of this Timeline.
        """
        return self._timelines

    def add_static_actor(self, actor):
        """Adds an actor or list of actors as static actor/s which will not be
        controlled nor animated by the Timeline. All static actors will be
        added to the scene when the Timeline is added to the scene.

        Parameters
        ----------
        actor: vtkActor or list(vtkActor)
            Static actor/s.
        """
        self.add_actor(actor, static=True)

    @property
    def static_actors(self):
        """Returns a list of static actors.

        Returns
        -------
        list:
            List of static actors.
        """
        return self._static_actors

    def remove_timelines(self):
        """Removes all child Timelines from the Timeline"""
        self._timelines.clear()

    def remove_actor(self, actor):
        """Removes an actor from the Timeline.

        Parameters
        ----------
        actor: vtkActor
            Actor to be removed from the timeline.
        """
        self._items.remove(actor)

    def remove_actors(self):
        """Removes all actors from the Timeline"""
        self.clear()

    def update_animation(self, t=None, force=False, _in_scene=None):
        """Updates the timeline animations"""
        if t is None:
            t = self.current_timestamp
            if t > self._final_timestamp:
                if self._loop:
                    self.seek(0)
                else:
                    self.seek(self.final_timestamp)
                    # Doing this will pause both the timeline and the panel.
                    self.playback_panel.pause()
        if self.has_playback_panel and (self.playing or force):
            self.update_final_timestamp()
            self.playback_panel.current_time = t

        # handling in/out of scene events
        in_scene = self.is_inside_scene_at(t)
        if _in_scene is not None:
            in_scene = _in_scene and in_scene
        self.handle_scene_event(in_scene)

        if self.playing or force:
            if self._camera is not None:
                if self.is_interpolatable('rotation', is_camera=True):
                    pos = self._camera.GetPosition()
                    translation = np.identity(4)
                    translation[:3, 3] = pos
                    # camera axis is reverted
                    rot = - self.get_camera_rotation(t)
                    rot = transform.Rotation \
                        .from_euler('xyz', rot, degrees=True).as_matrix()
                    rot = np.array([[*rot[0], 0],
                                    [*rot[1], 0],
                                    [*rot[2], 0],
                                    [0, 0, 0, 1]])
                    rot = translation @ rot @ np.linalg.inv(translation)
                    self._camera.SetModelTransformMatrix(rot.flatten())

                if self.is_interpolatable('position', is_camera=True):
                    cam_pos = self.get_camera_position(t)
                    self._camera.SetPosition(cam_pos)

                if self.is_interpolatable('focal', is_camera=True):
                    cam_foc = self.get_camera_focal(t)
                    self._camera.SetFocalPoint(cam_foc)

                if self.is_interpolatable('view_up', is_camera=True):
                    cam_up = self.get_camera_view_up(t)
                    self._camera.SetViewUp(cam_up)
                elif not self.is_interpolatable('view_up', is_camera=True):
                    # to preserve up-view as default after user interaction
                    self._camera.SetViewUp(0, 1, 0)

            elif self._is_camera_animated and self._scene:
                self._camera = self._scene.camera()
                self.update_animation(force=True)
                return

            # actors properties
            if in_scene:
                if self.is_interpolatable('position'):
                    position = self.get_position(t)
                    self.SetPosition(position)

                if self.is_interpolatable('scale'):
                    scale = self.get_scale(t)
                    [act.SetScale(scale) for act in self.actors]

                if self.is_interpolatable('opacity'):
                    scale = self.get_opacity(t)
                    [act.GetProperty().SetOpacity(scale) for
                     act in self.actors]

                if self.is_interpolatable('rotation'):
                    euler = self.get_rotation(t)
                    [act.SetOrientation(euler) for
                     act in self.actors]

                if self.is_interpolatable('color'):
                    color = self.get_color(t)
                    for act in self.actors:
                        act.vcolors[:] = color * 255
                        utils.update_actor(act)
                # Also update all child Timelines.
            [tl.update_animation(t, force=True, _in_scene=in_scene)
             for tl in self.timelines]

    def play(self):
        """Play the animation"""
        if not self.playing:
            if self.current_timestamp >= self.final_timestamp:
                self.current_timestamp = 0
            self.update_final_timestamp()
            self._last_started_time = \
                time.perf_counter() - self._last_timestamp / self.speed
            self._playing = True

    def pause(self):
        """Pauses the animation"""
        self._last_timestamp = self.current_timestamp
        self._playing = False

    def stop(self):
        """Stops the animation"""
        self._last_timestamp = 0
        self._playing = False
        self.update_animation(force=True)

    def restart(self):
        """Restarts the animation"""
        self._last_timestamp = 0
        self._playing = True
        self.update_animation(force=True)

    @property
    def current_timestamp(self):
        """Get current timestamp of the Timeline.

        Returns
        ----------
        float
            The current time of the Timeline.

        """
        if self.playing:
            self._last_timestamp = (time.perf_counter() -
                                    self._last_started_time) * self.speed
        return self._last_timestamp

    @current_timestamp.setter
    def current_timestamp(self, timestamp):
        """Set the current timestamp of the Timeline.

        Parameters
        ----------
        timestamp: float
            The time to set as current time of the Timeline.

        """
        self.seek(timestamp)

    @property
    def final_timestamp(self):
        """Get the final timestamp of the Timeline.

        Returns
        ----------
        float
            The final time of the Timeline.

        """
        return self._final_timestamp

    def seek(self, timestamp):
        """Sets the current timestamp of the Timeline.

        Parameters
        ----------
        timestamp: float
            The time to seek.

        """
        # assuring timestamp value is in the timeline range
        if timestamp < 0:
            timestamp = 0
        elif timestamp > self.final_timestamp:
            timestamp = self.final_timestamp

        if self.playing:
            self._last_started_time = \
                time.perf_counter() - timestamp / self.speed
        else:
            self._last_timestamp = timestamp
            self.update_animation(force=True)

    def seek_percent(self, percent):
        """Seek a percentage of the Timeline's final timestamp.

        Parameters
        ----------
        percent: float
            Value from 1 to 100.

        """
        t = percent * self._final_timestamp / 100
        self.seek(t)

    @property
    def playing(self):
        """Returns whether the Timeline is playing.

        Returns
        -------
        bool
            Timeline is playing if True.
        """
        return self._playing

    @playing.setter
    def playing(self, playing):
        """Sets the playing state of the Timeline.

        Parameters
        ----------
        playing: bool
            The playing state to be set.

        """
        self._playing = playing

    @property
    def stopped(self):
        """Returns whether the Timeline is stopped.

        Returns
        -------
        bool
            Timeline is stopped if True.

        """
        return not self.playing and not self._last_timestamp

    @property
    def paused(self):
        """Returns whether the Timeline is paused.

        Returns
        -------
        bool
            Timeline is paused if True.

        """

        return not self.playing and self._last_timestamp is not None

    @property
    def speed(self):
        """Returns the speed of the timeline.

        Returns
        -------
        float
            The speed of the timeline's playback.
        """
        return self._speed

    @speed.setter
    def speed(self, speed):
        """Set the speed of the timeline.

        Parameters
        ----------
        speed: float
            The speed of the timeline's playback.

        """
        current = self.current_timestamp
        if speed <= 0:
            return
        self._speed = speed
        self._last_started_time = time.perf_counter()
        self.current_timestamp = current

    @property
    def has_playback_panel(self):
        return self.playback_panel is not None

    def add_to_scene(self, ren):
        super(Timeline, self).add_to_scene(ren)
        [ren.add(static_act) for static_act in self._static_actors]
        [ren.add(timeline) for timeline in self.timelines]
        self._scene = ren
        self._added_to_scene = True
        self.update_animation(force=True)
        if self._motion_path_actor:
            ren.add(self._motion_path_actor)
