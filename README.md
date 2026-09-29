# Efficient palette-based decomposition and recoloring of images via RGBXY-space geometry

This code implements the pipeline described in the SIGGRAPH Asia 2018 paper ["Efficient palette-based decomposition and recoloring of images via RGBXY-space geometry"](https://cragl.cs.gmu.edu/fastlayers/) Jianchao Tan, Jose Echevarria, and Yotam Gingold.

A different and simpler prototype implementation can be found in [this link](https://cragl.cs.gmu.edu/fastlayers/RGBXY_weights.py)

## Running the GUI

The GUI runs entirely in the browser. The Python code runs in a Web Worker via [Pyodide](https://pyodide.org/), so there is nothing to install.
It only needs to be served over HTTP from the root of this repository (the worker loads the Python files). For example:

    python3 -m http.server

and then open <http://localhost:8000/>. (Any static web host, such as GitHub Pages, works too.)
The first visit downloads Python, NumPy, and SciPy (a few tens of megabytes); your browser caches them after that.

Alternatively, the GUI can use the Python WebSocket server (for example, to use OpenCL). See "Running the Server" below.

Load or drag-and-drop an image. Then compute the palette and weights. You can manipulate the palette colors in the 3D RGB-space view. You can save the palette and weights for recoloring by clicking the "Save Everything" button, which downloads a zip file containing them, the original image, the layers, and more.

Some videos of GUI usage can be found in [this link](https://cragl.cs.gmu.edu/fastlayers/)

The `turquoise.png` image is copyright [Michelle Lee](https://cargocollective.com/michellelee).

### Image Recoloring

You can perform global recoloring with the resulting layers with a different web GUI (no installation necessary).

1. Unzip `<image name>-everything.zip` from "Save Everything". Go to <https://yig.github.io/image-rgb-in-3D/>
2. Drag and drop the original image: `<image name>`
3. Drag and drop the palette: `<image name>-automatic computed palette-modified.js`
4. Drag and drop the weights: `<image name>-weights.js`
5. Click and drag the palette vertices in the 3D view to perform image recoloring.

This image recoloring web GUI is also used in our previous project, [Decomposing Images into Layers via RGB-space Geometry](https://github.com/JianchaoTan/Decompose-Single-Image-Into-Layers).

## Running the Server

The server is optional. The GUI uses it instead of computing in the browser when you open it with a `server` or `port` parameter: <http://localhost:8000/image-layer-updating-GUI/?server> (default port 9988) or <http://localhost:8000/image-layer-updating-GUI/?port=9988>.

### With Docker

You can run the server via Docker (no need to install any dependencies on your machine). You won't get an OpenCL implementation of the layer updating, but it is still quite fast.

    docker pull cragl/fastlayers
    docker run -p 8000:8000 -p 9988:9988 cragl/fastlayers

Then open <http://localhost:8000/image-layer-updating-GUI/?server>.

### Without Docker

#### Installing dependencies

You can install dependencies using either `conda` or `pip`.

##### Conda

Install [Anaconda](https://www.anaconda.com/products/individual) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html).
(Miniconda is faster to install.) Choose the 64-bit Python 3.x version. Launch the Anaconda shell from the Start menu and navigate to this directory.
Then:

    conda env create -f environment.yml
    conda activate fastlayers

To update an already created environment if the `environment.yml` file changes, first activate and then run `conda env update --file environment.yml --prune`.

##### Pip

Note: One of our dependencies, `cvxopt`, is broken on Apple Silicon with `pip`. Use the `conda` instructions above, or skip `cvxopt`; it is optional (without it, SciPy's HiGHS linear programming solver is used).

Install Python 3.6+.

(Optional) Create a virtual environment:

    python3 -m venv .venv
    source .venv/bin/activate

Install dependencies:

    pip install -r requirements.txt

(untested) If you want to install the exact version of the dependencies we used, run: `pip install -r requirements.frozen.txt`

#### On your own

* Python 3.6+
* Python
* NumPy
* SciPy
* (optional) [GLPK](https://www.gnu.org/software/glpk/) (`brew install glpk`)
* (optional) cvxopt, built with the [GLPK](https://www.gnu.org/software/glpk/) linear programming solver interface (`CVXOPT_BUILD_GLPK=1 pip install cvxopt`)
* PIL or Pillow (Python Image Library) (`pip install Pillow`)
* (optional) pyopencl
* websockets (`pip install websockets`)

#### Running the server

Run the server:

    cd image-layer-updating-GUI
    ./runboth.sh

Then open <http://localhost:8000/image-layer-updating-GUI/?server>.

If you are on Windows (untested), the `runboth.sh` script probably won't work. Instead, run the two Python server commands manually in two separate command lines:

    cd image-layer-updating-GUI
    python3 server.py

and

    python3 -m http.server


### Testing

To test the whole pipeline without launching the GUI server, run `Our_preprocessing_pipeline.ipynb` as a Jupyter notebook.

You can test if your installation is working by comparing your output to the `test/turquoise groundtruth results/` directory.
