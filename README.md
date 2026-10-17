# MathHacks2.0-TempName-

Achievements/Stuff we did:

- Replaced Ursina's point by point mesh builder with a NumPy version that calculates the whole grid at once, instead of for loops, and hands it to the GPU in a single block instead of thousands of separate objects, making rebuilds around 40x faster. Since only the heights change, we only build the triangles and texture maps once, at the start.

For libraries:
python -m pip install -r requirements.txt
