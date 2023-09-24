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
    BreakAndMakePhaseSwitchComponent,
    PhaseScoreComponent,
    AssembleStepTargetRecorder,
    MaxInstances,
)

class SteppedBreakAndMakeEnvConfig(VisualInterfaceConfig, LoaderConfig):
    image_height = 256
    image_width = 256
    render_mode = 'egl'
    compute_collision_map = False
    
    max_time_steps = 48
    max_instances = None

    truncate_if_assembly_unchanged = False

class SteppedBreakAndMakeEnv(SuperMechaContainer):
    def __init__(self,
        config,
        train=False,
        rank=None,
        size=None,
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
            config, components['scene'], train=train, rank=rank, size=size)
        
        # time step
        components['time'] = TimeStepComponent(
            config.max_time_steps, observe_step=False)
        
        # initial assembly
        components['initial_assembly'] = AssemblyComponent(
            components['scene'],
            update_on_init=False,
            update_on_reset=True,
            update_on_step=False,
            observable=True,
            compute_collision_map=False, #True,
        )
        
        # visual interface
        config.include_done = False
        config.include_phase = True
        config.include_assemble_step = True
        interface_components = make_visual_interface(
            config,
            components['scene'],
            train=train,
        )
        
        # separate out the render and nonrender components from the interface
        render_components = {
            k:v for k,v in interface_components.items()
            if 'render' in k
        }
        nonrender_components = {
            k:v for k,v in interface_components.items()
            if 'render' not in k
        }
        components.update(nonrender_components)
        
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
            compute_collision_map=config.compute_collision_map,
            truncate_if_unchanged=(
                config.truncate_if_assembly_unchanged * train),
        )
        components['target_image'] = AssembleStepTargetRecorder(
            components['image'],
            components['action_primitives'].components['assemble_step'],
            components['action_primitives'].components['phase'],
            zero_out_of_bounds=True,
        )
        components['target_assembly'] = AssembleStepTargetRecorder(
            components['assembly'],
            components['action_primitives'].components['assemble_step'],
            components['action_primitives'].components['phase'],
            zero_phase_zero=True,
        )
        components.update(render_components)
        
        # score
        score_component = BuildScore(
            components['initial_assembly'],
            components['assembly'],
            normalize=True,
        )
        components['score'] = PhaseScoreComponent(
            #components['phase'],
            components['action_primitives'].components['phase'],
            score_component,
        )
        
        if config.max_instances is not None:
            components['max_instances'] = MaxInstances(
                components['scene'], config.max_instances)
        
        super().__init__(components)
    
    def reset_loader(self):
        self.components['loader'].reset_iterator()
    
    def step(self, *args, **kwargs):
        o,r,t,u,i = super().step(*args, **kwargs)
        if self.components['loader'].finished:
            t = False
            u = False
        
        return o,r,t,u,i
