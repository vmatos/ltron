import time
import numpy

import brick_gym.utils as utils
import brick_gym.evaluation as evaluation
import brick_gym.gym.spaces as bg_spaces
from brick_gym.gym.components.brick_env_component import BrickEnvComponent

class InstanceGraphConstructionTask(BrickEnvComponent):
    def __init__(self,
            num_classes,
            max_instances,
            max_edges,
            scene_component,
            dataset_component):
        
        self.num_classes = num_classes
        self.max_instances = max_instances
        self.max_edges = max_edges
        self.scene_component = scene_component
        self.dataset_component = dataset_component
        
        self.action_space = bg_spaces.InstanceGraphSpace(
                self.num_classes, self.max_instances, self.max_edges,
                include_edge_score=True,
                include_instance_score=True)
        
        self.true_edges = None
        self.true_instances = None
    
    def reset(self):
        
        # compute the target  edges for this episode
        self.true_edges = {}
        
        brick_scene = self.scene_component.brick_scene
        scene_connections = brick_scene.get_all_snap_connections()
        class_lookup = self.dataset_component.dataset_info['class_ids']
        for instance_a in scene_connections:
            brick_instance_a = brick_scene.instances[instance_a]
            class_a = class_lookup[str(brick_instance_a.brick_type)]
            for instance_b, snap_id in scene_connections[instance_a]:
                brick_instance_b = brick_scene.instances[instance_b]
                id_a = int(instance_a)
                id_b = int(instance_b)
                class_b = class_lookup[str(brick_instance_b.brick_type)]
                if id_a < id_b:
                    self.true_edges[(id_a, id_b, class_a, class_b)] = 1.0
        
        self.true_instances = {}
        for instance in brick_scene.instances:
            instance_id = int(instance)
            brick_instance = brick_scene.instances[instance]
            class_label = class_lookup[str(brick_instance.brick_type)]
            self.true_instances[(instance_id, class_label)] = 1.0
        
        return None
    
    def step(self, action):
        ###################3
        #ta = time.time()
        
        edge_index = action['edges']['edge_index']
        edge_score = action['edges']['score']
        assert edge_index.shape[1] <= self.max_edges
        unidirectional_edges = edge_index[0] < edge_index[1]
        edge_index = edge_index[:,unidirectional_edges]
        edge_scores = action['edges']['score'][unidirectional_edges]
        
        ###################3
        #tb = time.time()
        #print('graph_task ab:', tb-ta)
        #print(edge_index.shape)
        #print(edge_scores.shape)
        #print(action['instances']['label'].shape)
        #print(action['instances']['num_instances'])
        
        predicted_edges = utils.sparse_graph_to_edge_scores(
                image_index = None,
                node_label = action['instances']['label'],
                edges = edge_index.T,
                scores = edge_score,
        )
        
        ###################3
        #tc = time.time()
        #print('graph_task bc:', tc-tb)
        
        _, _, edge_ap = evaluation.edge_ap(predicted_edges, self.true_edges)
        
        ###################3
        #td = time.time()
        #print('graph_task cd:', td-tc)
        
        predicted_instances = utils.sparse_graph_to_instance_scores(
                image_index = None,
                indices = range(len(action['instances']['label'])),
                instance_labels = action['instances']['label'],
                scores = action['instances']['score'],
        )
        
        ###################3
        #te = time.time()
        #print('graph_task de:', te-td)
        
        _, _, instance_ap = evaluation.edge_ap(
                predicted_instances, self.true_instances)
        
        ###################3
        #tf = time.time()
        #print('graph_task ef:', tf-te)
        
        info = {'instance_ap' : instance_ap,
                'edge_ap' : edge_ap,
        }
        
        terminal = False
        num_instances = action['instances']['num_instances']
        if num_instances >= self.max_instances:
            terminal = True
        
        ###################3
        #tg = time.time()
        #print('graph_task final:', tg-tf)
        
        return None, edge_ap, terminal, info

'''
class GraphConstructionTask(BrickEnvComponent):
    def __init__(self,
            num_classes,
            max_nodes,
            scene_component):
        
        self.num_classes = num_classes
        self.max_nodes = max_nodes
        self.scene_component = scene_component
        self.scene_component.brick_scene.make_track_snaps()
        
        self.action_space = bg_spaces.GraphScoreSpace(
                self.num_classes, self.max_nodes)
    
    def step(self, action):
        predicted_edge_scores = utils.matrix_to_edge_scores(
                None, action['nodes'], action['edges'])
        target_edge_scores = GET_SCENE_GRAPH
        _, _, ap = evaluation.edge_ap(
                predicted_edge_scores, target_edge_scores)
        
        return None, ap, False, None
    
    #def get_predicted_edge_scores(self, action):
    #    predicted_edge_scores = utils.matrix_to_edge_scores(
    #            None, predicted_graph['nodes'], predicted_graph['edges'])
    #    return predicted_edge_scores
    #
    #def compute_reward(self, state, action):
    #    scene_metadata = state[self.scene_metadata_key]
    #    target_edge_scores = utils.metadata_to_edge_scores(
    #            None, scene_metadata)
    #    predicted_edge_scores = self.get_predicted_edge_scores(action)
    #    _, _, ap = evaluation.edge_ap(
    #            predicted_edge_scores, target_edge_scores)
    #    return ap

class SparseGraphConstructionTask(GraphConstructionTask):
    def __init__(self,
            num_classes,
            max_nodes,
            max_edges,
            graph_key='graph',
            scene_metadata_key='scene_metadata'):
        
        self.max_edges = max_edges
        super(SparseGraphReconstructionTask, self).__init__(
                num_classes=num_classes,
                max_nodes=max_nodes,
                graph_key=graph_key,
                scene_metadata_key=scene_metadata_key)
    
    def update_action_space(self, action_space):
        action_space[self.graph_key] = bg_spaces.SparseGraphScoreSpace(
                self.num_classes, self.max_nodes, self.max_edges)
    
    def get_predicted_edge_scores(self, action):
        predicted_sparse_graph = action[self.graph_key]
        predicted_edge_scores = utils.sparse_graph_to_edge_scores(
                None,
                predicted_sparse_graph['nodes'],
                predicted_sparse_graph['edges'],
                predicted_sparse_graph['scores'])
        return predicted_edge_scores
'''
