import random

from gym.spaces import Discrete, Dict

from ltron.dataset.paths import (
        get_dataset_paths, get_dataset_info, get_metadata)
import ltron.gym.spaces as bg_spaces
from ltron.gym.components.brick_env_component import BrickEnvComponent

class DatasetPathComponent(BrickEnvComponent):
    def __init__(self,
            dataset,
            split,
            subset=None,
            rank=0,
            size=1,
            reset_mode='uniform',
            augment_dataset=None,
            p_augment = 0.5,
            observe_episode_id=False):
        
        self.reset_mode = reset_mode
        self.dataset = dataset
        self.augment_dataset = augment_dataset
        self.p_augment = p_augment
        self.split = split
        self.subset = subset
        self.dataset_info = get_dataset_info(self.dataset)
        if reset_mode == 'multi_pass':
            self.dataset_paths = get_dataset_paths(
                    self.dataset, self.split, self.subset)
        else:
            self.dataset_paths = get_dataset_paths(
                    self.dataset, self.split, self.subset, rank, size)
        
        if self.augment_dataset is not None:
            self.augment_info = get_dataset_info(self.augment_dataset)
            self.augment_paths = get_dataset_paths(
                    self.augment_dataset, 'all')
        
        self.observe_episode_id = observe_episode_id
        if self.observe_episode_id:
            self.all_dataset_paths = get_dataset_paths(
                    self.dataset, self.split)
            self.observation_space = Dict({
                'episode_id':Discrete(len(self.all_dataset_paths)+1)})
        
        if self.reset_mode == 'multi_pass':
            start_episode = rank * len(self.dataset_paths) // size
            self.set_state({'episode' : start_episode, 'scene_path' : None})
        else:
            self.set_state({'episode' : 0, 'scene_path' : None})
    
    def observe(self):
        self.observation = None
        if self.observe_episode_id:
            self.observation = {'episode_id':0}
            if self.scene_path is not None:
                try:
                    self.observation['episode_id'] = (
                        self.all_dataset_paths.index(self.scene_path))
                except ValueError:
                    pass
    
    def reset(self):
        if (self.augment_dataset is not None and
                random.random() < self.p_augment):
            self.scene_path = random.choice(self.augment_paths)
        else:
            if self.reset_mode == 'uniform':
                self.scene_path = random.choice(self.dataset_paths)
            elif (self.reset_mode == 'sequential' or
                    self.reset_mode == 'multi_pass'):
                self.scene_path = self.dataset_paths[
                        self.episode % len(self.dataset_paths)]
            elif self.reset_mode == 'single_pass':
                if self.episode < len(self.dataset_paths):
                    self.scene_path = self.dataset_paths[self.episode]
                else:
                    self.scene_path = None
            else:
                raise ValueError('Unknown reset mode "%s"'%self.reset_mode)
            if self.scene_path is not None:
                self.episode += 1
        
        self.observe()
        return self.observation
    
    def step(self, action):
        self.observe()
        return self.observation, 0., False, None
    
    def get_state(self):
        state = {'episode' : self.episode, 'scene_path' : self.scene_path}
       
    def set_state(self, state):
        self.episode = state['episode']
        self.scene_path = state['scene_path']
    
    def get_class_id(self, class_name):
        return self.dataset_info['class_ids'][class_name]
