#### Vectorized closest point on a triangle, in pure NumPy.
#### Replaces the Cython GteDistPointTriangle module so that everything also runs
#### in the browser (Pyodide), where Cython extensions can't be compiled.
#### Algorithm: "Real-Time Collision Detection" (Ericson 2005), Section 5.1.5.

from __future__ import print_function, division

import numpy as np


def closest_points_on_triangle(points, triangle):
    '''
    Given:
        points: an N-by-3 array of points
        triangle: a 3-by-3 array of triangle vertices
    Returns:
        distances: a length-N array of distances from each point to the triangle
        closest: an N-by-3 array of the closest point on the triangle to each point
    '''
    points = np.asarray(points, dtype=float).reshape((-1, 3))
    a, b, c = np.asarray(triangle, dtype=float)
    ab = b - a
    ac = c - a

    ap = points - a
    d1 = ap.dot(ab)
    d2 = ap.dot(ac)
    bp = points - b
    d3 = bp.dot(ab)
    d4 = bp.dot(ac)
    cp = points - c
    d5 = cp.dot(ab)
    d6 = cp.dot(ac)

    vc = d1*d4 - d3*d2
    vb = d5*d2 - d1*d6
    va = d3*d6 - d5*d4

    with np.errstate(divide='ignore', invalid='ignore'):
        ## Barycentric coordinates (u,v,w) of the closest point for each Voronoi region,
        ## in the same priority order as Ericson's if-chain.
        t_ab = d1/(d1 - d3)
        t_ac = d2/(d2 - d6)
        t_bc = (d4 - d3)/((d4 - d3) + (d5 - d6))
        denom = 1./(va + vb + vc)
        v_in = vb*denom
        w_in = vc*denom

        conditions = [
            (d1 <= 0) & (d2 <= 0),                                  ## vertex a
            (d3 >= 0) & (d4 <= d3),                                 ## vertex b
            (vc <= 0) & (d1 >= 0) & (d3 <= 0),                      ## edge ab
            (d6 >= 0) & (d5 <= d6),                                 ## vertex c
            (vb <= 0) & (d2 >= 0) & (d6 <= 0),                      ## edge ac
            (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0),        ## edge bc
            ]
        v = np.select(conditions, [0., 1., t_ab, 0., 0., 1. - t_bc], v_in)
        w = np.select(conditions, [0., 0., 0., 1., t_ac, t_bc], w_in)

    closest = a + v[:, None]*ab + w[:, None]*ac
    distances = np.sqrt(((points - closest)**2).sum(axis=1))
    ## A degenerate (zero-area) triangle can produce NaNs. Make them lose any min().
    distances[np.isnan(distances)] = np.inf
    return distances, closest


def closest_points_on_triangles(points, triangles):
    '''
    Given:
        points: an N-by-3 array of points
        triangles: an F-by-3-by-3 array of triangles
    Returns:
        distances: a length-N array of distances from each point to the nearest triangle
        closest: an N-by-3 array of the closest point on the nearest triangle to each point
    '''
    points = np.asarray(points, dtype=float).reshape((-1, 3))
    best_distances = np.full(len(points), np.inf)
    best_closest = points.copy()
    for triangle in triangles:
        distances, closest = closest_points_on_triangle(points, triangle)
        better = distances < best_distances
        best_distances[better] = distances[better]
        best_closest[better] = closest[better]
    return best_distances, best_closest
