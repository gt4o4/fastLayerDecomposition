/**
 * A drop-in replacement for WebSocketClient (websocket-client.js) that
 * talks to layer-worker.js, which runs the layer decomposition in the browser.
 * @example
 * const client = new WorkerClient;
 * client.onstatus = text => console.log( text );
 * await client.connect( 'js/layer-worker.js' );
 * client.send( 'automatically-compute-palette' );
 * console.log( await client.receive() );
 */
class WorkerClient {

    constructor() {
        this._worker = null;
        this._error = null;
        this._receiveDataQueue = [];
        this._receiveCallbacksQueue = [];
        // Called with progress text from the worker ('' when idle).
        this.onstatus = null;
    }

    /**
     * Whether the worker is running.
     * Messages sent before the worker finishes loading are queued, so
     * this is true as soon as connect() is called.
     */
    get connected() {
        return this._worker !== null && this._error === null;
    }

    /**
     * The number of messages available to receive.
     */
    get dataAvailable() {
        return this._receiveDataQueue.length;
    }

    /**
     * Starts the worker at `url`.
     */
    connect( url ) {
        this.disconnect();

        this._worker = new Worker( url, { type: 'module' } );
        this._worker.onmessage = event => {
            const msg = event.data;
            if( msg.type === 'data' ) {
                if( this._receiveCallbacksQueue.length !== 0 ) {
                    this._receiveCallbacksQueue.shift().resolve( msg.data );
                } else {
                    this._receiveDataQueue.push( msg.data );
                }
            }
            else if( msg.type === 'status' ) {
                if( this.onstatus ) this.onstatus( msg.text );
            }
            else if( msg.type === 'error' ) {
                if( this.onstatus ) this.onstatus( "Error: " + msg.text );
                // The request that failed won't get a response.
                if( this._receiveCallbacksQueue.length !== 0 ) {
                    this._receiveCallbacksQueue.shift().reject( new Error( msg.text ) );
                }
            }
        };
        this._worker.onerror = event => {
            this._error = new Error( event.message );
            if( this.onstatus ) this.onstatus( "Error: " + event.message );
            while( this._receiveCallbacksQueue.length !== 0 ) {
                this._receiveCallbacksQueue.shift().reject( this._error );
            }
        };

        return Promise.resolve();
    }

    /**
     * Send data to the worker.
     */
    send( data ) {
        if( !this.connected ) {
            throw this._error || new Error( 'Not connected.' );
        }

        this._worker.postMessage( data );
    }

    /**
     * Asynchronously receive data from the worker.
     * @returns A promise that resolves with the data received.
     */
    receive() {
        if( this._receiveDataQueue.length !== 0 ) {
            return Promise.resolve( this._receiveDataQueue.shift() );
        }

        if( !this.connected ) {
            return Promise.reject( this._error || new Error( 'Not connected.' ) );
        }

        return new Promise( ( resolve, reject ) => {
            this._receiveCallbacksQueue.push({ resolve, reject });
        });
    }

    /**
     * Stops the worker.
     */
    disconnect() {
        if( this._worker !== null ) this._worker.terminate();
        this._worker = null;
        this._error = null;
        this._receiveDataQueue = [];
        this._receiveCallbacksQueue = [];
        return Promise.resolve();
    }
}
