import numpy

import gymnasium as gym

import splendor.contexts.glut as glut
from splendor.image import save_image

from ltron.constants import SHAPE_CLASS_LABELS, COLOR_CLASS_LABELS
from ltron.gym.envs import (
    FreebuildEnvConfig,
    BreakEnvConfig,
    MakeEnvConfig,
)
from ltron.gym.components import ViewpointActions

class LtronInterfaceConfig(FreebuildEnvConfig, BreakEnvConfig, MakeEnvConfig):
    seed = 1234567890
    env_name = 'LTRON/Freebuild-v0'
    train = True
    auto_reset = True

class LtronInterface:
    def __init__(self, config):
        self.env = gym.make(
            config.env_name,
            config=config,
            train=config.train,
        )
        if config.auto_reset:
            self.env = gym.wrappers.AutoResetWrapper(self.env)
        self.env.reset(seed=config.seed)
        
        self.scene = self.env.components['scene'].brick_scene
        self.window = self.scene.render_environment.window
        self.renderer = self.scene.render_environment.renderer
        
        self.button = 0
        self.click = (0,0)
        self.release = (0,0)
        
        self.window.register_callbacks(
            glutDisplayFunc = self.render,
            glutIdleFunc = self.render,
            glutKeyboardFunc = self.key_press,
            glutSpecialFunc = self.special_key_press,
            glutMouseFunc = self.mouse_button,
            glutMotionFunc = self.mouse_move,
        )
    
    def render(self):
        self.window.set_active()
        self.window.enable_window()
        self.scene.color_render(flip_y=False)
    
    def dump_image(self, image_path):
        self.window.set_active()
        self.window.enable_window()
        self.scene.color_render(flip_y=False)
        image = self.window.read_pixels()[::-1]
        print('Saving image to: %s'%image_path)
        save_image(image, image_path)
    
    def dump_scene(self, scene_path):
        self.scene.export_ldraw(scene_path)
    
    def key_press(self, key, x, y):
        if key == b'r':
            self.env.reset()
            return
        
        elif key == b'\r':
            print('Please specify an output image file path:')
            file_path = input()
            self.dump_image(file_path)
            return
        
        elif key == b'\\':
            print('Please specify an output scene file path:')
            file_path = input()
            self.dump_scene(file_path)
            return
        
        action = self.env.no_op_action()
        
        # pick and place
        if key == b'p':
            # pick and place
            action['action_primitives']['mode'] = 1
            action['action_primitives']['pick_and_place'] = 1
        
        # rotate
        elif key == b'[':
            action['action_primitives']['mode'] = 2
            action['action_primitives']['rotate'] = 18 #1
        
        elif key == b']':
            action['action_primitives']['mode'] = 2
            action['action_primitives']['rotate'] = 22 #3
        
        # table viewpoint
        elif key == b'w':
            action['action_primitives']['mode'] = 0
            action['action_primitives']['viewpoint'] = (
                ViewpointActions.ELEVATION_NEG.value)
        
        elif key == b's':
            action['action_primitives']['mode'] = 0
            action['action_primitives']['viewpoint'] = (
                ViewpointActions.ELEVATION_POS.value)
        
        elif key == b'a':
            action['action_primitives']['mode'] = 0
            action['action_primitives']['viewpoint'] = (
                ViewpointActions.AZIMUTH_NEG.value)
        
        elif key == b'd':
            action['action_primitives']['mode'] = 0
            action['action_primitives']['viewpoint'] = (
                ViewpointActions.AZIMUTH_POS.value)
        
        elif key == b'q':
            action['action_primitives']['mode'] = 0
            action['action_primitives']['viewpoint'] = (
                ViewpointActions.DISTANCE_NEG.value)
        
        elif key == b'e':
            action['action_primitives']['mode'] = 0
            action['action_primitives']['viewpoint'] = (
                ViewpointActions.DISTANCE_POS.value)
        
        elif key == b'\x08':
            action['action_primitives']['mode'] = 3
            action['action_primitives']['remove'] = 1
        
        elif key == b'\t':
            print('Please enter the shape and color separated by commas:')
            text = input()
            try:
                s,c = text.split(',')
                s = SHAPE_CLASS_LABELS[s]
                c = COLOR_CLASS_LABELS[c]
            except:
                print('Misformatted input, expected two comma-separated ints')
                s = 0
                c = 0
            action['action_primitives']['mode'] = 4
            action['action_primitives']['insert'] = numpy.array([s,c])
        
        action['cursor']['button'] = self.button
        action['cursor']['click'] = self.click
        action['cursor']['release'] = self.release
        
        
        o,r,t,u,i = self.env.step(action)
        print('Reward:%.02f Terminal:%s Truncated:%s'%(r, t, u))
    
    def special_key_press(self, key, x, y):
        
        action = self.env.no_op_action()
        if key == 100:
            action['action_primitives']['mode'] = 0
            action['action_primitives']['viewpoint'] = (
                ViewpointActions.X_NEG.value)
        
        if key == 101:
            action['action_primitives']['mode'] = 0
            action['action_primitives']['viewpoint'] = (
                ViewpointActions.Y_POS.value)
        
        if key == 102:
            action['action_primitives']['mode'] = 0
            action['action_primitives']['viewpoint'] = (
                ViewpointActions.X_POS.value)
        
        if key == 103:
            action['action_primitives']['mode'] = 0
            action['action_primitives']['viewpoint'] = (
                ViewpointActions.Y_NEG.value)
        
        if key == 107: # end
            action['phase'] = 1
        
        o,r,t,u,i = self.env.step(action)
        print('Reward:%.02f Terminal:%s Truncated:%s'%(r, t, u))
    
    def mouse_button(self, button, button_state, x, y):
        if button == 0 or button == 2:
            if button_state == 0:
                self.click = (y,x)
                if button == 0:
                    self.button = 0
                elif button == 2:
                    self.button = 1
            else:
                self.release = (y,x)
    
    def mouse_move(self, x, y):
        pass

def ltron_env_interface():
    config = LtronInterfaceConfig.from_commandline()
    config.render_mode = 'glut'
    interface = LtronInterface(config)
    
    glut.start_main_loop()

if __name__ == '__main__':
    ltron_env_interface()
