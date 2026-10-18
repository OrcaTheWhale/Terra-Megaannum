# MathHacks2.0-TempName-

Achievements/Stuff we did:
- Replaced Ursina's point by point mesh builder with a NumPy version that calculates the whole grid at once, instead of for loops, and hands it to the GPU in a single block instead of thousands of separate objects, making rebuilds around 40x faster. Since only the heights change, we only build the triangles and texture maps once, at the start.
  
  For libraries: python -m pip install -r requirements.txt

How the Simulator’s Calculations Work:
- The simulator represents terrain as a grid of height values. Each point initially has a value between 0 and 255, with bigger values showing higher ground. Calculations update the height, estimate weather, measure changes, and generate the visible rivers.
  
Height and Elevation:
- The simulator converts heightmap values into elevations using the minimum and maximum elevations specified in the settings.
With the current range of 0 to 1500 meters, a heightmap value of 0 represents sea level, while 255 represents 1500 meters. Values between these limits are converted proportionally. This elevation conversion is used to estimate temperature at different heights. The displayed size of the terrain is controlled separately and does not determine its real elevation.

Simulation Time:
- Each simulation step represents one day, one season, or one year. A season is treated as 91.25 days, and a year contains exactly 365 days.
The simulator tracks elapsed time by adding the duration of every completed step. It uses this total to determine the displayed year, day, and season.
The speed settings control how many simulation steps run during each frame. Increasing the speed makes simulated time pass faster on screen without changing the duration represented by an individual step.
When the user returns to an earlier step, the simulator displays a stored copy of the terrain. Continuing from that point removes the later steps and starts a new continuation.

Soil Creep:
- Soil creep gradually smooths the terrain.
For each grid point, the simulator finds the average height of its four direct neighbours. It then moves the point’s height partway toward that average. High points become lower, while depressions become higher.
The amount of change depends on the creep rate and the duration of the simulation step. The current rate is deliberately accelerated so changes are visible during a demonstration.
Long steps are divided into smaller internal updates to keep the calculation stable. With the default settings, a one-day step uses one update, a season uses ten, and a year uses thirty-seven.
At the boundaries, the simulator repeats the nearest edge height when a neighbour would fall outside the map. This prevents material from being transferred beyond the terrain.
The calculation redistributes height across the grid and should preserve the total height sum, apart from small rounding differences.

Seasonal Temperature:
- Sea-level temperature follows a smooth, repeating seasonal cycle.
The current settings use an annual average of 5°C and a seasonal variation of 15°C above or below that average. This produces temperatures ranging from approximately −10°C to 20°C before additional warming is applied.
The warmest point in the cycle is set to day 200.
For steps lasting a season or a year, the simulator calculates the average temperature across the entire interval. It does not use only the temperature at the beginning of the step. A complete year averages to the configured annual temperature plus any warming adjustment.
This is a simplified climate cycle, rather than a daily weather forecast.

Temperature at Higher Elevations:
- The simulator assumes that temperature decreases by 6.5°C for every 1000 metres of elevation.
At 1500 meters, the calculated temperature is therefore 9.75°C colder than the sea-level temperature.
The simulator applies this adjustment to every point on the terrain. It then counts how many points are below 0°C and expresses that count as a percentage of the whole map.
For longer steps, this percentage uses the step’s average temperature. It does not measure how long each location remains frozen.
Temperature currently affects the climate information shown on screen. It does not change the soil-creep calculation.

Sensor Smoothing and Calibration:
- Most sensor readings are smoothed to reduce sudden fluctuations. Each new measurement moves the stored reading 20% of the way toward the latest value. This makes the display steadier, although it also makes it respond more gradually.
The first reading is stored directly. Timestamps and wind direction are not smoothed.
Light, flame, humidity, and tilt readings are converted to a scale from zero to one using calibration endpoints. Readings outside those endpoints are limited to the nearest end of the scale.
Light and flame readings use reversed calibration because lower raw readings represent stronger detection. Humidity readings from 40 to 90 are mapped across the scale, while tilt readings from 0° to 30° determine the displayed wind strength.
The interface labels normalized humidity as “rain.” This is a demonstration input, not a measurement of rainfall. Wind strength is similarly based on tilt rather than a measured wind speed.

Sensor Temperature Changes:
-The first valid temperature reading becomes the starting reference.
Later readings are compared with that reference to determine how much warmer or colder the sensor has become. This difference shifts the simulator’s climate temperatures.
Manual keyboard adjustments are added to the sensor difference. Each Up or Down input changes the manual adjustment by 0.5°C.
Re-zeroing replaces the starting reference with the current smoothed temperature.
The other sensor readings are currently displayed without affecting terrain evolution or river flow.

Percentage of Land Changed:
- The simulator compares each current height with its original height.
A point counts as changed when the difference is greater than one height unit. The number of changed points is divided by the total number of points and expressed as a percentage.
With the current elevation range, one height unit represents approximately 5.88 metres.
This measurement shows how much of the grid has crossed the change threshold. It does not describe the average size of those changes.

Percentage of Soil Moved:
- The simulator adds up the height lost at points that are now lower than their original positions. It compares this total with the sum of the original terrain heights.
Height gains are excluded so the calculation does not count both a loss and its corresponding deposit.
This describes net height loss relative to the starting terrain. It does not track every movement during intermediate steps. Material could move several times without all of that movement appearing in the final percentage.
The result is a height-based indicator. It is not a direct measurement of soil mass or volume.

Total Soil and Roughness:
- The displayed total soil value is the sum of all terrain heights. Under soil creep, this should remain approximately constant because the calculation redistributes material within the grid.
Converting this value into physical soil volume or mass would require additional information, including the area represented by each grid point.
Roughness is calculated using the standard deviation of the terrain heights. It measures how spread out the elevations are around their average.
A larger value indicates greater overall elevation variation. A smaller value indicates a more level landscape. This measurement does not directly describe local steepness or small surface details.

Likelihood Score:
- The simulator tests how sensitive its result is to small changes in its assumptions.
It repeats the recorded simulation with different starting heights and creep rates. Each alternative run changes the creep rate by up to 25% in either direction and independently adjusts each starting height by up to one height unit.
The alternative runs use the same recorded step durations and enabled conditions as the main simulation.
Each final height is compared with the corresponding height in the main result. A comparison counts as agreement when the difference is no more than two height units.
The displayed score is the percentage of agreeing comparisons across all grid points and alternative runs.
For example, a score of 90% means that 90% of these individual comparisons were within the selected tolerance. It does not mean there is a 90% probability that the entire landscape will develop that way in reality.
The calculation uses between five and twenty alternative runs. It estimates how many to perform from the duration of the first run, aiming for approximately three seconds of processing.

Uncertainty Map: 
- The uncertainty map measures how much the alternative simulations disagree at each location.
At every grid point, the simulator calculates the standard deviation of the alternative final heights. Higher values indicate greater disagreement, while lower values indicate more consistent results.
This uncertainty reflects the starting-height and creep-rate variations included in the calculation. It does not account for every possible source of error.

River Placement:
- The river system first smooths the original terrain to reduce the influence of small irregularities.
Each point checks its eight surrounding neighbours and selects the lowest one. Flow moves onward only if that neighbour is strictly lower. Otherwise, the point becomes a stopping location.
This method chooses the lowest neighbouring elevation. It does not account for the longer distance of diagonal moves or calculate how water would overflow enclosed depressions.
The river-mask helper can blend an original reference surface with updated terrain, giving the reference 75% of the influence. The active river system currently creates its layout from the original terrain.

River Flow Accumulation:
- Every point starts with one unit of contributing flow.
The simulator processes points from highest to lowest. Each point passes its accumulated contribution to its downhill neighbour. Lower locations therefore collect contributions from the upstream points that drain into them.
The resulting value represents contributing drainage area in grid points. It is not a physical flow rate.
A point becomes a river channel when its accumulated contribution reaches a threshold. This threshold is adjusted for map size so smaller maps can still produce streams.
The current model assumes equal contribution from every point. Humidity sensor readings do not change this calculation.

River Width and Mountain Coverage:
- Larger accumulated flows produce wider rivers. Width grows logarithmically, so large rivers widen gradually instead of expanding in direct proportion to their upstream contributions.
The simulator finds each point’s distance from the nearest channel. Nearby points can become wet if they fall within the channel’s calculated width and are no more than 1.15 height units above the nearest channel location.
This limits water coverage on elevated banks.
The simulator also identifies high terrain using the 70th elevation percentile. It limits wet coverage within that group to 25%, keeping the lower wet locations when the limit is exceeded.
These are visual placement rules rather than a complete flooding model.

Optional River Erosion:
- The water module includes erosion helpers that are not currently used by the main simulation.
These helpers assign stronger incision to channels with greater accumulated flow. The strength increases logarithmically and is limited to a fixed range.
Material can then be removed from channels and redistributed to surrounding banks. The deposition weights are normalized so that, when suitable bank locations exist, the total amount deposited matches the amount removed.
The current visible rivers do not perform this erosion.

Terrain Rendering:
- The terrain mesh places grid points across a normalized horizontal area and converts their heights into vertical positions. The display scale then stretches this mesh to its visible size.
Each square between neighbouring grid points is divided into two triangles, allowing the graphics engine to draw the surface.
The renderer estimates slopes in both horizontal directions and uses them to calculate surface normals. These describe the direction each part of the terrain faces and allow lighting to respond to its shape.
Triangle connections and texture coordinates are created once. Later updates reuse the mesh and replace its heights and normals.

Water Rendering and Animation:
- Each wet location receives a small surface made from two triangles. Neighbouring surfaces overlap slightly to reduce visible gaps.
The corners sample the terrain between grid points so the water follows the landscape. A small vertical offset raises it above the ground to reduce flickering.
When the terrain changes, the water moves vertically to follow it. Its drainage paths are not recalculated.
The blue water texture is generated using repeating mathematical waves. One pattern creates narrow bright ripple crests, while another adds changes in brightness.
Texture placement depends partly on terrain elevation, helping the ripples follow the landscape. The texture shifts over time to create the appearance of flowing water.
This animation is visual. It does not calculate physical water velocity.

Procedural Terrain Generation:
- The procedural generator creates terrain using simplex noise.
It combines four layers of noise. Each successive layer has twice the sampling frequency and half the amplitude of the previous layer. Broad layers create larger features, while finer layers add smaller variations.
The frequency setting controls how much variation fits into the image. A random seed selects the terrain pattern.
Noise values are converted into grayscale values between 0 and 255 and saved as a heightmap.
The current main program loads the configured heightmap image. It does not automatically run the procedural generator.

Saved Maps and Charts:
- The change map compares current heights with original heights. Red represents height loss, while blue represents height gain. Equal-sized losses and gains use comparable colour intensity.
The history chart shows how the land-changed and soil-moved percentages develop over simulated time. A separate axis displays the recorded sea-level temperature.
The uncertainty map shows where alternative simulation runs produce the greatest differences.


