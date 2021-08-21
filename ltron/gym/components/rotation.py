import numpy
from ltron.gym.spaces import SinglePixelSelectionSpace
from ltron.gym.components.ltron_gym_component import LtronGymComponent
from gym.spaces import (
    Discrete,
    Tuple,
    Dict,
    MultiDiscrete
)
from ltron.geometry.collision import check_collision
import math

class RotationAroundSnap(LtronGymComponent):
    def __init__(
        self, sceneComp, pos_snap_render, neg_snap_render, check_collisions
    ):
        self.scene_component = sceneComp
        self.pos_snap_render = pos_snap_render
        self.neg_snap_render = neg_snap_render
        self.check_collisions = check_collisions
        width = self.pos_snap_render.width
        height = self.pos_snap_render.height
        assert self.neg_snap_render.width == width
        assert self.neg_snap_render.height == height
        #self.action_space = MultiDiscrete([2, width, height, 180])
        self.action_space = Dict({
            'activate':Discrete(2),
            'polarity':Discrete(2),
            'direction':Discrete(2),
            'pick':SinglePixelSelectionSpace(width, height),
        })

        self.observation_space = Dict({'success': Discrete(2)})

    def reset(self):
        return {'success':0}
    
    # I moved this to brick_scene because I needed it other places as well
    #def transform_about_snap(
    #    self, polarity, instance_id, snap_id, transform, scene
    #):
    #    instance = scene.instances[instance_id]
    #    snap_transform = instance.get_snap(snap_id).transform
    #    prototype_transform = instance.brick_type.snaps[snap_id].transform
    #    instance_transform = (
    #            snap_transform @
    #            transform @
    #            numpy.linalg.inv(prototype_transform))

    #    table = scene.instances.instances
    #    c_polarity = '-+'[polarity]

    #    scene.move_instance(instance, instance_transform)
    #    snap_transform = instance.get_snap(snap_id).transform

    def step(self, action):

        if action is None: return {'rotation_suceed' : 0}, 0, False, None

        activate = action['activate']
        if not activate:
            return {'success':0}, 0, False, None
        polarity = action['polarity']
        direction = action['direction']
        if direction:
            degree = math.radians(90)
        else:
            degree = math.radians(-90)
        (y_cord, x_cord) = action['pick']
        trans = numpy.eye(4)
        rotate_x = numpy.copy(trans)
        rotate_x[1,1] = math.cos(degree)
        rotate_x[1,2] = -math.sin(degree)
        rotate_x[2:1] = math.sin(degree)
        rotate_x[2:2] = math.cos(degree)
        
        rotate_y = numpy.copy(trans)
        rotate_y[0,0] = math.cos(degree)
        rotate_y[0,2] = math.sin(degree)
        rotate_y[2,0] = -math.sin(degree)
        rotate_y[2,2] = math.cos(degree)

        rotate_z = numpy.copy(trans)
        rotate_z[0,0] = math.cos(degree)
        rotate_z[0,1] = -math.sin(degree)
        rotate_z[1,0] = math.sin(degree)
        rotate_z[1,1] = math.cos(degree)

        if polarity == 1:
            rotate_map = self.pos_snap_render.observation
        else:
            rotate_map = self.neg_snap_render.observation
        
        instance_id, snap_id = rotate_map[y_cord, x_cord]
        if instance_id == 0:
            return {'success' : 0}, 0, False, None
        #self.transform_about_snap(polarity, instance_id, snap_id, rotate_y, self.scene_component.brick_scene)
        
        scene = self.scene_component.brick_scene
        instance = scene.instances[instance_id]
        snap = instance.get_snap(snap_id)
        scene.transform_about_snap([instance], snap, rotate_y)

        return {'success' : 1}, 0, False, None
