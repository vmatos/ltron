#!/usr/bin/env python
#import brick_gym.torch.train.graph_d as graph_d
import brick_gym.torch.train.test_graph as test_graph

#run = 'Jan24_01-28-20_mechagodzilla'
#epoch = 200
#run = 'Feb10_11-50-54_gpu3'
run = 'Feb17_22-57-19_gpu3' #'Feb17_22-57-19_gpu3'
epoch = 500

if __name__ == '__main__':
    test_graph.test_checkpoint(
            # load checkpoints
            step_checkpoint = './checkpoint/%s/step_model_%04i.pt'%(run, epoch),
            edge_checkpoint = './checkpoint/%s/edge_model_%04i.pt'%(run, epoch),
            
            # dataset settings
            dataset = 'tiny_turbos2',
            num_processes = 4,
            test_split = 'train',
            test_subset = 4,
            
            # model settings
            step_model_name='nth_try',
<<<<<<< HEAD
=======
            decoder_channels=512,
>>>>>>> e172d5a2b25d7fc0dd302a691e7261057ca3dc6e
            step_model_backbone='simple',
            segment_id_matching=False,
            
            # output settings
            dump_debug=False)
