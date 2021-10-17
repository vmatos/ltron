import time

import numpy

import tqdm

from scipy.spatial import cKDTree

from ltron.geometry.grid_bucket import GridBucket

def match_configurations(
    config_a,
    config_b,
    kdtree=None,
    radius=0.01,
):
    '''
    Note: This is optimized for the case where config_b is larger than config_a
    '''
    
    # Build the kdtree if one was not passed in.
    if kdtree is None:
        kdtree = cKDTree(config_b['pose'][:,:3,3])
    
    # Initialize the set of matches that have been tested already.
    ab_tested_matches = set()
    
    # Filter the poses in a to only contain non-zero entries
    
    # Order the classes from least common to common.
    # This makes it more likely that we will find a good match sooner.
    unique_a, count_a = numpy.unique(config_a['class'], return_counts=True)
    sort_order = numpy.argsort(count_a)
    class_order = unique_a[sort_order]
    
    best_alignment = None
    best_matches = set()
    best_offset = numpy.eye(4)
    
    matched_a = set()
    matched_b = set()
    
    finished = False
    while not finished:
        finished = True
        for c in class_order:
            if c == 0:
                continue
            
            instance_indices_b = numpy.where(config_b['class'] == c)[0]
            if not len(instance_indices_b):
                continue
            
            instance_indices_a = numpy.where(config_a['class'] == c)[0]
            
            for a in instance_indices_a:
                color_a = config_a['color'][a]
                for b in instance_indices_b:
                    # If a and b are matched under the current best offset
                    # even if they are not matched to each other, don't
                    # consider this offset.
                    if a in matched_a and b in matched_b:
                        continue
                    
                    # If the offset between a and b has already been tested
                    # don't reconsider this offset.
                    if (a,b) in ab_tested_matches:
                        continue
                    
                    # If the colors don't match, do not consider this offset.
                    color_b = config_b['color'][b]
                    if color_a != color_b:
                        continue
                    
                    # Compute the offset between a and b.
                    pose_a = config_a['pose'][a]
                    pose_b = config_b['pose'][b]
                    a_to_b = pose_b @ numpy.linalg.inv(pose_a)
                    transformed_a = numpy.matmul(a_to_b, config_a['pose'])
                    #transformed_a = numpy.matmul(a_to_b, sparse_poses_a)
                    
                    # Compute the closeset points.
                    pos_a = transformed_a[:,:3,3]
                    matches = kdtree.query_ball_point(pos_a, radius)
                    #matches = [[] for _ in config_a['class']]
                    #for i, sparse_match in zip(sparse_id_a, sparse_matches):
                    #    matches[i] = sparse_match
                    
                    # If the number of matches is less than the current best
                    # skip the validation step.
                    potential_matches = sum(
                        1 for c, m in zip(config_a['class'], matches)
                        if len(m) and c != 0
                    )
                    if potential_matches <= len(best_matches):
                        continue
                    
                    # Validate the matches.
                    valid_matches = validate_matches(
                        config_a, config_b, matches, a_to_b)
                    
                    # Update the set of tested matches with everything that was
                    # matched in this comparison, this avoids reconsidering the
                    # same offset later.
                    ab_tested_matches.update(valid_matches)
                    
                    # If the number of valid matches is the best so far, update
                    # and break.  Breaking will exit all the way out to the
                    # main while loop and start over from the beginning.
                    # This is important because
                    # it allows us to reconsider offsets that we might have
                    # skipped because of the first short-circuit in this block.
                    # Two bricks a and b may have been connected in the previous
                    # alignment, but may not be connected after this better
                    # alignment, so now we need to consider them again.
                    # As convoluted as this is, it saves a ton of computation.
                    if len(valid_matches) > len(best_matches):
                        best_alignment = (a,b)
                        best_matches.clear()
                        best_matches.update(valid_matches)
                        best_offset = a_to_b
                        matched_a.clear()
                        matched_b.clear()
                        matched_a.update(set(a for a,b in valid_matches))
                        matched_b.update(set(b for a,b in valid_matches))
                        finished = False
                        break
                
                # If we just found a new best, start over from the beginning
                if not finished:
                    break
            
            # If we just found a new best, start over from the beginning
            if not finished:
                break
    
    # Return.
    return best_matches, best_offset

def validate_matches(config_a, config_b, matches, a_to_b):
    # Ensure that classes match, colors match, poses match and that each brick
    # is only matched to one other.
    valid_matches = set()
    for a, a_matches in enumerate(matches):
        for b in a_matches:
            class_a = config_a['class'][a]
            class_b = config_b['class'][b]
            if class_a != class_b or class_a == 0 or class_b == 0:
                continue
            
            color_a = config_a['color'][a]
            color_b = config_b['color'][b]
            if color_a != color_b:
                continue
            
            transformed_pose_a = a_to_b @ config_a['pose'][a]
            pose_b = config_b['pose'][b]
            if not numpy.allclose(transformed_pose_a, pose_b):
                continue
            
            valid_matches.add((a,b))
            break
    
    return valid_matches

def match_lookup(matching, a_config, b_config):
    a_to_b = {a:b for a, b in matching}
    b_to_a = {b:a for a, b in matching}
    a_instances = numpy.where(a_config['class'] != 0)[0]
    miss_a = set(a for a in a_instances if a not in a_to_b)
    b_instances = numpy.where(b_config['class'] != 0)[0]
    miss_b = set(b for b in b_instances if b not in b_to_a)
    
    return a_to_b, b_to_a, miss_a, miss_b
