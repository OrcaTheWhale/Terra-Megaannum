import numpy as np
from ursina import Entity, Mesh
#script to abandon ursina's built in builder; it checks in a for loop, this checks in NumPy to increase speed and calculations

class FastTerrain(Entity):
    def __init__(self, heights, **kwargs):
        w, d = heights.shape
        self.w, self.d = w, d
        # how tall the terrain is drawn compared to how wide (for slope_degrees), from the scale given
        scale = kwargs.get('scale', (1, 1, 1))
        self.height_ratio = scale[1] / scale[0]

        #create the flat grid from -0.5 to 0.5
        X, Z = np.meshgrid(np.linspace(-0.5, 0.5, w), np.linspace(-0.5, 0.5, d))
        self._verts = np.zeros((d, w, 3), np.float32)
        self._verts[..., 0] = X
        self._verts[..., 2] = Z
        self._normals = np.zeros((d, w, 3), np.float32)

        #coordinate the Terrain and the picture
        U, V = np.meshgrid(np.arange(w) / w, np.arange(d) / d)
        #convert to a single array for the gpu, so instead of reading each and every square, it reads the whole array at once, which is much faster
        uvs = np.stack([U, V], axis=-1).astype(np.float32).ravel()

        #create triangles for the mesh, since graphics only takes triangles, and using NumPy instead of a for loop
        idx = np.arange(w * d).reshape(d, w)
        #drop the last row and column, then multiply w*l and get the # of squares, and then multiply by 2 to get the # of triangles. Then send the triangles to the GPU as a single array
        a, b = idx[1:, 1:], idx[1:, :-1]
        c, e = idx[:-1, :-1], idx[:-1, 1:]
        triangles = np.stack([a, b, c, c, e, a], axis=-1).astype(np.uint32).ravel()
        #recalculating
        self._fill(heights)
        mesh = Mesh(vertices=self._verts.ravel(), triangles=triangles, uvs=uvs, normals=self._normals.ravel(), static=False)
        super().__init__(model=mesh, **kwargs)

    def _fill(self, heights):
        h = (heights.T / 255).astype(np.float32)        # rows = z, columns = x
        self._verts[..., 1] = h
        #check which way each point faces for lighting.
        #each point has a "normal", in which the direction it faces. Measure the slope everywhere to find where it points to the sun:
        #gradient returns the slope by getting the x and z axis, which takes the next value, and takes n2-n1 / 2 for the slope.
        gz, gx = np.gradient(h, 1 / (self.d - 1), 1 / (self.w - 1))
        # slope of the terrain as drawn on screen, in degrees (scaled by how tall vs wide it's drawn).
        # Not used yet; the shader works out steepness itself from the normals.
        self.slope_degrees = np.degrees(np.arctan(np.hypot(gx, gz) * self.height_ratio))
        n = self._normals
        #turn the slope into arrows
        #rising x (+), and leaning toward -x
        n[..., 0], n[..., 1], n[..., 2] = -gx, 1, -gz
        #make the arrow length 1
        n /= np.linalg.norm(n, axis=-1, keepdims=True)

    def set_heights(self, heights):
        #Update the shape. Call this instead of building a new Terrain.
        self._fill(heights)
        self.model.vertices = self._verts.ravel()
        self.model.normals = self._normals.ravel()
        self.model.generate()
