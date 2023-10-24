from collections import OrderedDict

from supermecha import (
    SuperMechaComponent,
    SuperMechaContainer,
    TimeStepComponent,
)

from ltron.dataset.info import get_dataset_info
from ltron.gym.components import (
    EmptySceneComponent,
    LoaderConfig,
    make_loader,
    ClearScene,
    VisualInterfaceConfig,
    make_visual_interface,
    ColorRenderComponent,
    AssemblyComponent,
    BuildScore,
    PlaceAboveScene,
    PartialDisassemblyComponent,
)

class MakeEnvConfig(VisualInterfaceConfig, LoaderConfig):
    load_start_scene = None
    
    max_time_steps = 1000000
    image_height = 256
    image_width = 256
    render_mode = 'egl'
    
    image_based_target = False
    use_place_above_for_start = False
    randomize_place_above_orientation = False
    place_above_orientation_mode = 24
    place_above_selection = 'highest'
    number_to_remove = 1
    compute_collision_map = False
    min_removal_remaining = 1
    
    truncate_if_assembly_unchanged = False

    max_instances = None
    
    multi_click_map = False
    old_island_style = False
    log_prob_losses = False
    expert_matches_at_identity = True
    expert_action_selection = 'random'

class MakeEnv(SuperMechaContainer):
    def __init__(self,
        config,
        train=False,
    ):
        components = OrderedDict()
        
        # scene
        if config.render_mode == 'egl':
            render_args = None
        elif config.render_mode == 'glut':
            render_args = {
                'opengl_mode' : 'glut',
                'window_width' : config.image_width,
                'window_height' : config.image_height,
                'load_scene' : 'front_light',
            }
        components['scene'] = EmptySceneComponent(
            renderable=True,
            render_args=render_args,
            track_snaps=True,
            collision_checker=True,
        )
        
        # loader
        components['loader'] = make_loader(
            config, components['scene'], train=train)
        
        # time step
        components['time'] = TimeStepComponent(
            config.max_time_steps, observe_step=True)
        
        # visual interface
        interface_components = make_visual_interface(
            config,
            components['scene'],
            train=train,
        )
        render_components = {
            k:v for k,v in interface_components.items()
            if 'render' in k
        }
        nonrender_components = {
            k:v for k,v in interface_components.items()
            if 'render' not in k
        }
        components.update(nonrender_components)
        
        components['partial_disassembly'] = PartialDisassemblyComponent(
            components['scene'],
            min_remaining=config.min_removal_remaining)
        
        if config.image_based_target:
            components['target_image'] = ColorRenderComponent(
            components['scene'],
            config.image_height,
            config.image_width,
            anti_alias=True,
            update_on_init=False,
            update_on_reset=True,
            update_on_step=False,
            observable=True,
        )
        components['target_assembly'] = AssemblyComponent(
            components['scene'],
            update_on_init=False,
            update_on_reset=True,
            update_on_step=False,
            observable=True,
            compute_collision_map=config.compute_collision_map
        )
        
        if config.use_place_above_for_start:
            components['place_above_scene'] = PlaceAboveScene(
                components['scene'],
                offset=(-96,48,-96),
                randomize_orientation=config.randomize_place_above_orientation,
                randomize_orientation_mode=config.place_above_orientation_mode,
                selection_mode=config.place_above_selection,
                #number_to_remove=config.number_to_remove,
            )
        else:
            if config.load_start_scene is None:
                components['clear_scene'] = ClearScene(
                    components['scene'],
                    update_on_init=True,
                    update_on_reset=True,
                )
            else:
                components['start_loader'] = make_loader(
                    config,
                    components['scene'],
                    train=train,
                    load_key='load_start_scene',
                )
        
        # color render
        components['image'] = ColorRenderComponent(
            components['scene'],
            config.image_height,
            config.image_width,
            anti_alias=True,
            update_on_init=False,
            update_on_reset=True,
            update_on_step=True,
            observable=True,
        )
        components['assembly'] = AssemblyComponent(
            components['scene'],
            update_on_init=False,
            update_on_reset=True,
            update_on_step=True,
            observable=True,
            truncate_if_unchanged=config.truncate_if_assembly_unchanged,
        )
        components.update(render_components)
        
        # score
        components['score'] = BuildScore(
            components['target_assembly'],
            components['assembly'],
        )
        
        super().__init__(components)
    
    def reset_loader(self):
        self.components['loader'].reset_iterator()
    
    def get_loaded_scene(self):
        return self.components['loader'].file_name
    
    def step(self, *args, **kwargs):
        o,r,t,u,i = super().step(*args, **kwargs)
        if self.components['loader'].finished:
            t = False
            u = False
        
        return o,r,t,u,i
