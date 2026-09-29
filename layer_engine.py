'''
The computations behind the interactive layer-editing GUI, independent of transport.
Used by the WebSocket server (image-layer-updating-GUI/server.py) and
by the in-browser Pyodide Web Worker (image-layer-updating-GUI/js/layer-worker.js).
'''

from __future__ import print_function, division

import json
import numpy as np
from scipy.spatial import ConvexHull

import Additive_mixing_layers_extraction
Additive_mixing_layers_extraction.DEMO=True

## A flag for using OpenCL.
## In particular for Docker, pocl doesn't implement something we need,
## so let's not install it in Docker and instead run without OpenCL.
## When using pocl, I get:
##     Device side queue is unimplemented (clCreateCommandQueueWithProperties.c:93)
USE_OPENCL = False
try:
    import pyopencl_example
    if len( pyopencl_example.cl.get_platforms() ) > 0:
        USE_OPENCL = True
except: pass
print( "Using OpenCL:", USE_OPENCL )


def palette_hull_json( palette ):
    '''
    Given a palette as an N-by-3 array in [0,1], returns the JSON string the GUI expects:
    the palette and its convex hull faces, in [0,255].
    '''
    hull=ConvexHull(palette)
    return json.dumps( {'vs': (palette*255).tolist(), 'faces': (hull.points[hull.simplices]*255).tolist() } )


class LayerEngine( object ):
    def __init__( self ):
        self.the_image = None
        self.RGBXY_mixing_weights = None
        self.data_hull = None

    def load_image( self, width, height, data ):
        '''
        Given the image width, height, and its RGBA bytes (row-major, uint8),
        precomputes the RGBXY mixing weights.
        '''
        the_image_new = np.frombuffer( data, dtype = np.uint8 ).reshape(height, width, 4 ).copy()

        ## Skip load image if we already have this exact image.
        if self.the_image is not None and self.the_image.shape == the_image_new.shape and np.all(self.the_image == the_image_new):
            print( "Skipping duplicate load-image." )
            return

        the_image = self.the_image = the_image_new
        print( "Received an image with", the_image.nbytes, "bytes." )

        # Compute RGBXY_mixing_weights.
        print( "Computing RGBXY mixing weights ..." )
        X,Y=np.mgrid[0:the_image.shape[0], 0:the_image.shape[1]]
        XY=np.dstack((X*1.0/the_image.shape[0],Y*1.0/the_image.shape[1]))
        RGBXY_data=np.dstack((the_image[:,:,:3]/255.0, XY))
        print( "\tConvexHull 5D..." )
        self.data_hull=ConvexHull(RGBXY_data.reshape((-1,5)))
        print( "\t...finished" )
        print( "\tComputing W_RGBXY..." )
        self.RGBXY_mixing_weights=Additive_mixing_layers_extraction.recover_ASAP_weights_using_scipy_delaunay(self.data_hull.points[self.data_hull.vertices], self.data_hull.points, option=3)
        print( "\t...finished" )
        print( "... finished." )

    def layers( self, palette ):
        '''
        Given a palette as a JSON string of RGB triplets in [0,255],
        returns the layer weights as bytes: a height-by-width-by-len(palette) uint8 array.
        '''
        the_image = self.the_image
        data_hull = self.data_hull
        RGBXY_mixing_weights = self.RGBXY_mixing_weights

        palette = json.loads( palette )
        palette = np.asarray(palette)/255.0
        num_layers = len( palette )

        ### compute RGB_mixing_weights and use pyopencl version code to dot product with sparse RGBXY_mixing_weights
        img_data=(the_image[:,:,:3].reshape((-1,3))[data_hull.vertices]).reshape((-1,1,3))/255.0
#### delaunay triangulation.
        # w_rgb=RGBXY_method.run_one_ASAP(palette, img_data, None)
#### star triangulation using close to black pigment as first color
        w_rgb=Additive_mixing_layers_extraction.Get_ASAP_weights_using_Tan_2016_triangulation_and_then_barycentric_coordinates(img_data, palette, "None", order=0)

        w_rgb=w_rgb.reshape((-1,num_layers))

        if USE_OPENCL:
            w_rgbxy_values=RGBXY_mixing_weights.data
            w_rgbxy_values=w_rgbxy_values.reshape((-1,6))
            w_rgbxy_indices=RGBXY_mixing_weights.indices.reshape((-1,6))

            mult, _ = pyopencl_example.prepare_openCL_multiplication( w_rgb, w_rgbxy_values, w_rgbxy_indices )
            final_mixing_weights=mult(w_rgb)
        else:
            final_mixing_weights = RGBXY_mixing_weights.dot( w_rgb )

        layers=final_mixing_weights.reshape((the_image.shape[0], the_image.shape[1], num_layers))
        ## HACK: Send uint8 for speed.
        return np.ascontiguousarray( ( layers*255. ).round().clip(0,255), np.uint8 ).tobytes()

    def automatically_compute_palette( self ):
        '''
        Returns an automatically-sized palette and its convex hull as a JSON string.
        '''
        palette=Additive_mixing_layers_extraction.Hull_Simplification_determined_version(self.the_image[:,:,:3].reshape((-1,3))/255.0, "./example-", SAVE=False)
        print ("finish compute palette")
        return palette_hull_json( palette )

    def compute_palette_with_size( self, palette_size ):
        '''
        Returns a palette with `palette_size` colors and its convex hull as a JSON string.
        '''
        palette=Additive_mixing_layers_extraction.Hull_Simplification_old(self.the_image[:,:,:3].reshape((-1,3))/255.0, palette_size, "./example-")
        print ("finish compute palette")
        return palette_hull_json( palette )

    def palette_hull( self, palette ):
        '''
        Given a palette as a JSON string of RGB triplets in [0,255],
        returns it along with its convex hull as a JSON string.
        '''
        palette = np.asarray( json.loads( palette ) )/255.0
        return palette_hull_json( palette )
