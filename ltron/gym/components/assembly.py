import numpy

from supermecha import SensorComponent

from ltron.constants import (
    SHAPE_CLASS_LABELS,
    COLOR_CLASS_LABELS,
    MAX_INSTANCES_PER_SCENE,
    MAX_EDGES_PER_SCENE,
)
from ltron.bricks.brick_scene import TooManyInstancesError, make_empty_assembly
from ltron.gym.spaces import AssemblySpace
from ltron.geometry.collision import build_collision_map

class AssemblyComponent(SensorComponent):
    def __init__(self,
        scene_component,
        shape_class_labels=None,
        color_class_labels=None,
        max_instances=None,
        max_edges=None,
        update_on_init=False,
        update_on_reset=False,
        update_on_step=False,
        observable=True,
        compute_collision_map=False,
    ):
        super().__init__(
            update_on_init=update_on_init,
            update_on_reset=update_on_reset,
            update_on_step=update_on_step,
            observable=observable,
        )
        
        self.scene_component = scene_component
        #self.shape_ids = shape_ids
        #self.color_ids = color_ids
        self.shape_class_labels = shape_class_labels
        self.color_class_labels = color_class_labels
        if max_instances is None:
            max_instances = MAX_INSTANCES_PER_SCENE
        self.max_instances = max_instances
        if max_edges is None:
            max_edges = MAX_EDGES_PER_SCENE
        self.max_edges = max_edges
        
        if self.observable:
            self.observation_space = AssemblySpace(
                self.max_instances,
                self.max_edges,
            )
        
        self.compute_collision_map = compute_collision_map
    
    def compute_observation(self):
        assembly = self.scene_component.brick_scene.get_assembly(
            shape_class_labels=self.shape_class_labels,
            color_class_labels=self.color_class_labels,
            max_instances=self.max_instances,
            max_edges=self.max_edges,
        )
        if self.compute_collision_map:
            self.collision_map = build_collision_map(
                self.scene_component.brick_scene,
            )
        
        return assembly, {}

class DeduplicateAssemblyComponent(SensorComponent):
    def __init__(self,
        assembly_component,
        update_frequency='step',
        observable=True,
    ):
        super().__init__(
            update_frequency=update_frequency,
            observable=observable,
        )
        self.assembly_component = assembly_component
        self.max_instances = self.assembly_component.max_instances
        
        if observable:
            self.observation_space = MaskedAssemblySpace(self.max_instances)
    
    def reset(self):
        super().reset()
        self.previous_shape = numpy.zeros(
            self.max_instances+1, dtype=numpy.long)
        self.previous_color = numpy.zeros(
            self.max_instances+1, dtype=numpy.long)
        self.previous_pose = numpy.zeros(
            (self.max_instances+1, 4, 4), dtype=numpy.float)
    
    def update_observation(self):
        # get the new assembly
        new_assembly = self.assembly_component.observe()
        
        # compare it the shape, color and pose
        shape_match = self.previous_shape == new_assembly['shape']
        color_match = self.previous_color == new_assembly['color']
        pose_match = self.previous_pose == new_assembly['pose']
        pose_match = numpy.all(pose_match, axis=(1,2))
        
        # store a mask indicating the elements that have changed
        self.observation = ~(shape_match & color_match & pose_match)
