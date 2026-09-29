/*
A Web Worker that runs the layer decomposition Python code in the browser via Pyodide.
It speaks the same message protocol as server.py (see protocol.txt), so that
WorkerClient (worker-client.js) is a drop-in replacement for WebSocketClient.

Messages posted back to the page are objects:
    { type: 'data', data }: a response, analogous to a WebSocket message.
    { type: 'status', topic, text }: progress text to show the user ('' when done).
    { type: 'error', topic, text }: an error. A pending receive() rejects.
`topic` is the protocol message being handled (e.g., 'palette'), or 'startup'.
*/

// This is a module worker, since Pyodide doesn't support classic workers.
import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs";
const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";

// The Python modules layer_engine.py needs, relative to the repository root.
const PYTHON_FILES = [
    "layer_engine.py",
    "Additive_mixing_layers_extraction.py",
    "Convexhull_simplification.py",
    "point_triangle_distance.py",
    "trimesh.py",
    ];
// This file is in <root>/image-layer-updating-GUI/js/
const REPOSITORY_ROOT = new URL( "../../", self.location );

// Queue incoming messages so we can `await receive()` them like the WebSocket server.
const inbox = [];
let waiting = null;
self.onmessage = event => {
    if( waiting !== null ) {
        const resolve = waiting;
        waiting = null;
        resolve( event.data );
    } else {
        inbox.push( event.data );
    }
};
function receive() {
    if( inbox.length !== 0 ) return Promise.resolve( inbox.shift() );
    return new Promise( resolve => { waiting = resolve; } );
}
function send( data ) { self.postMessage({ type: 'data', data: data }); }
// The protocol message currently being handled.
let topic = 'startup';
function status( text ) { self.postMessage({ type: 'status', topic: topic, text: text }); }
function error( text ) { self.postMessage({ type: 'error', topic: topic, text: text }); }

async function loadEngine() {
    status( "Loading Python (slow the first time)..." );
    const pyodide = await loadPyodide({ indexURL: PYODIDE_URL });
    await pyodide.loadPackage( [ "numpy", "scipy" ] );

    status( "Loading layer decomposition code..." );
    await Promise.all( PYTHON_FILES.map( async name => {
        const response = await fetch( new URL( name, REPOSITORY_ROOT ) );
        if( !response.ok ) throw new Error( "Could not load " + name + ": " + response.status );
        // The current directory is on Python's sys.path.
        pyodide.FS.writeFile( name, new Uint8Array( await response.arrayBuffer() ) );
    } ) );

    const engine = pyodide.pyimport( "layer_engine" ).LayerEngine();
    return { pyodide, engine };
}

async function main() {
    let pyodide, engine;
    try {
        ({ pyodide, engine } = await loadEngine());
    } catch( e ) {
        console.error( e );
        error( "Could not load the layer decomposition code: " + e.message );
        return;
    }
    status( "" );

    for( ;; ) {
        const msg = await receive();
        console.log( "worker:", msg );
        topic = msg;
        try {
            if( msg === "load-image" ) {
                const width_and_height = await receive();
                const data = await receive();
                const [ width, height ] = width_and_height.split( " " ).map( s => parseInt( s ) );
                status( "Pre-computing RGBXY weights..." );
                const buffer = pyodide.toPy( data );
                try { engine.load_image( width, height, buffer ); }
                finally { buffer.destroy(); }
            }
            else if( msg === "palette" ) {
                const palette = await receive();
                status( "Computing layers..." );
                const layers = engine.layers( palette );
                try {
                    // A Uint8Array. Transfer rather than copy its buffer.
                    const bytes = layers.toJs();
                    self.postMessage( { type: 'data', data: bytes }, [ bytes.buffer ] );
                }
                finally { layers.destroy(); }
            }
            else if( msg === "automatically-compute-palette" ) {
                status( "Computing automatic palette..." );
                send( engine.automatically_compute_palette() );
            }
            else if( msg === "user-choose-number-compute-palette" ) {
                const palette_size = parseInt( await receive() );
                status( "Computing palette..." );
                send( engine.compute_palette_with_size( palette_size ) );
            }
            else if( msg === "random-add-one-more-color" ) {
                const palette = await receive();
                send( engine.palette_hull( palette ) );
            }
            else {
                console.error( "Unknown message:", msg );
            }
            status( "" );
        } catch( e ) {
            console.error( e );
            error( e.message );
        }
    }
}

main();
