import numpy as np

def check_nstims(distances, events):
    val = list()
    for event in events:
        val.append(len(distances[event]))
    return min(val)

def test_distances(distances, events, method, mode, alternative):
    from scipy import stats
    distance_class = list()
    for event in events:
        if method == 'mean':
            distance_class.append(np.mean(np.array(distances[event])))
    I = np.argsort(distance_class)
    best = events[I[-1]]
    second_best = events[I[-2]]
    rest = events.copy()
    rest.remove(best) # modified in place

    if mode == 'best-rest':
        best_group = np.array(distances[best])
        another_group = list()
        for event in rest:
            another_group += distances[event]
        another_group = np.array(another_group)
    elif mode == 'best-second':
        best_group = np.array(distances[best])
        another_group = np.array(distances[second_best])
    else:
        raise ValueError("mode '%s' is not yet implemented."%mode)

    _, p = stats.ttest_ind(best_group, another_group, equal_var = False, alternative = alternative)
    
    pred = best
    
    return pred, p