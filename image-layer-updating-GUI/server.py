#!/usr/bin/env python3

import asyncio
import websockets
import sys
import os
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _parent_dir)

from layer_engine import LayerEngine

async def layer_server( websocket, path = None ):
    engine = LayerEngine()
    
    async for msg in websocket:
        print (msg)
        if msg == "load-image":
            ## Receive parameters from the websocket.
            width_and_height = await websocket.recv()
            data = await websocket.recv()
            
            ## Parse the parameters.
            width = int( width_and_height.split()[0] )
            height = int( width_and_height.split()[1] )
            engine.load_image( width, height, data )
        
        elif msg == "palette":
            ## Receive parameters from the websocket.
            palette = await websocket.recv()
            print (palette)
            
            layers = engine.layers( palette )
            print( "Sending weights..." )
            await websocket.send( layers )
            print( "... finished." )
        
        elif msg == "automatically-compute-palette":
            # No additional parameters. Compute an automatic palette for the image.
            await websocket.send( engine.automatically_compute_palette() )
        
        elif msg == "user-choose-number-compute-palette":
            palette_size=await websocket.recv()
            palette_size=int(palette_size)
            print ("user choose palette size is: ", palette_size)
            await websocket.send( engine.compute_palette_with_size( palette_size ) )
        
        elif msg == "random-add-one-more-color":
            palette = await websocket.recv()
            print (palette)
            await websocket.send( engine.palette_hull( palette ) )
        
        else:
            print( "Unknown message:", msg )



port_websocket = 9988
port_http = 8000

## Also start an http server on port 8000
def serve_http( port ):
    import os
    pid = os.fork()
    ## If we are the child, serve files
    if pid == 0:
        import http.server
        import socketserver
        ## Via: https://stackoverflow.com/questions/4465959/python-errno-98-address-already-in-use/25529620#25529620
        socketserver.TCPServer.allow_reuse_address
        Handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("localhost", port), Handler) as httpd:
            print("Serving HTTP on port", port)
            httpd.serve_forever()

## This is too annoying because of address re-use.
# serve_http( port_http )

import argparse
parser = argparse.ArgumentParser( description = "A compute server for interactive layer editing." )
parser.add_argument( "--port", type = int, default = port_websocket, help="The port to listen on." )
args = parser.parse_args()
port_websocket = args.port

print("WebSocket server on port", port_websocket )
start_server = websockets.serve( layer_server, '0.0.0.0', port_websocket, max_size = None )
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
