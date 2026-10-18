# MathHacks2.0-TempName-

Achievements/Stuff we did:
- Replaced Ursina's point by point mesh builder with a NumPy version that calculates the whole grid at once, instead of for loops, and hands it to the GPU in a single block instead of thousands of separate objects, making rebuilds around 40x faster. Since only the heights change, we only build the triangles and texture maps once, at the start.
  
  For libraries: python -m pip install -r requirements.txt

How the Simulator’s Calculations Work:
- The simulator represents terrain as a grid of height values. Each point initially has a value between 0 and 255, with bigger values showing higher ground. Calculations update the height, estimate climate and rainfall, grow vegetation, measure changes, and generate rivers and lakes.
  
Height and Elevation:
- The simulator converts heightmap values into elevations using the minimum and maximum elevations specified in the settings.
With the current range of 0 to 1500 meters, a heightmap value of 0 represents sea level, while 255 represents 1500 meters. Values between these limits are converted proportionally. This elevation conversion is used to estimate temperature at different heights. The displayed size of the terrain is controlled separately and does not determine its real elevation.

Simulation Time:
- Simulation steps can represent days, seasons, years, or longer intervals. A season is treated as 91.25 days, and a year contains exactly 365 days.
The simulator tracks elapsed time by adding the duration of every completed step. It uses this total to determine the displayed year, day, and season.
The speed settings control how many simulation steps run during each frame. Increasing the speed makes simulated time pass faster on screen without changing the duration represented by an individual step.
When the user returns to an earlier step, the simulator displays a stored copy of the terrain. Continuing from that point removes the later steps and starts a new continuation.

Soil Creep:
- Soil creep gradually smooths the terrain.
For each grid point, the simulator finds the average height of its four direct neighbours. It then moves the point’s height partway toward that average. High points become lower, while depressions become higher.
The amount of change depends on the diffusion coefficient, the duration of the simulation step, and the distance between grid points. The coefficient is 0.005 square metres per year.
Long steps are divided into smaller internal updates when needed to keep the calculation stable. The stability limit depends on grid spacing and the diffusion coefficient.
At the boundaries, the simulator repeats the nearest edge height when a neighbour would fall outside the map. This prevents material from being transferred beyond the terrain.
The calculation redistributes height across the grid and should preserve the total height sum, apart from small rounding differences.

Tectonic Uplift:
- Plate movement raises the terrain in a dome-shaped pattern. Uplift is fastest at the centre and falls to zero at the map edges.
The default maximum rate is 0.3 millimetres per year. Each step adds the local uplift rate multiplied by the step’s duration in years to the terrain height.

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
Temperature also determines the snow line, lake evaporation, and the temperature limit on vegetation. It does not change the soil-creep calculation.

Snow Line and Ice:
- The snow line is the elevation where the calculated temperature reaches 0°C. It is found by dividing sea-level temperature by the temperature decrease per kilometre of elevation.
The terrain shader draws snow above this line, and lakes and rivers above it turn to ice.
If the snow line is below sea level, the whole map freezes. If it is above the highest peak, no snow is drawn.
At a sea-level temperature of 5°C, the snow line is approximately 770 metres.

Wind-Driven Rainfall:
- Wind pushes air upward on slopes facing the wind. The rising air cools and releases moisture, giving those slopes more rain. Descending air produces drier conditions on the sheltered side, creating a rain shadow.
The calculation first smooths the terrain over 600 metres so rainfall responds to broad mountainsides.
Wind speed ranges from 2 to 20 metres per second as the wind-strength input rises from zero to one. The pendulum sensor or the Y key controls this input.
The rainfall pattern is rescaled so its average remains equal to the yearly rainfall selected in the menu. Wind redistributes rain across the map without changing that average.

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
Light controls vegetation growth, wind affects the rainfall pattern, and the flame sensor can burn vegetation. These inputs can therefore affect terrain evolution indirectly through plant cover and runoff.

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
- The displayed total soil value is the sum of all terrain heights. Under soil creep alone, this should remain approximately constant because the calculation redistributes material within the grid. Uplift adds material, while sediment leaving the map reduces it.
Converting this value into physical soil volume or mass would require additional information, including the area represented by each grid point.
Roughness is calculated using the standard deviation of the terrain heights. It measures how spread out the elevations are around their average.
A larger value indicates greater overall elevation variation. A smaller value indicates a more level landscape. This measurement does not directly describe local steepness or small surface details.

Likelihood Score:
- The simulator tests how sensitive its result is to small changes in its assumptions.
It repeats the recorded simulation twenty times. Each alternative run independently adjusts starting heights by up to one height unit and varies the process rates within their configured uncertainty ranges. These include soil creep by up to 80%, river erosion by up to 70%, and uplift by up to 50% in either direction.
The alternative runs use the same recorded history as the main simulation.
The score considers points where the main terrain changed by more than two height units, approximately 12 metres with the current elevation range. It compares the amount of change in each alternative run with the main result and counts agreement within a 25% tolerance.
The displayed score averages that agreement across the twenty runs.
A high score means the result remains similar under the tested variations. It does not mean there is that probability that the real landscape will develop that way.

Uncertainty Map: 
- The uncertainty map measures how much the alternative simulations disagree at each location.
At every grid point, the simulator calculates the standard deviation of the alternative final heights. Higher values indicate greater disagreement, while lower values indicate more consistent results.
This uncertainty reflects the starting-height and process-rate variations included in the calculation. It does not account for every possible source of error.

River Placement:
- The river system fills depressions to their lowest spill level before calculating drainage. It works inward from the map edges, processing the lowest unvisited point first.
This produces a surface on which enclosed hollows can drain toward an outlet. The difference between this filled surface and the ground identifies potential lake basins.
Each point checks its eight surrounding neighbours, including diagonals, and selects the lowest downhill receiver on the filled surface.
This method chooses the lowest neighbouring elevation rather than the steepest slope after accounting for diagonal distance.

River Flow Accumulation:
- The simulator processes points from highest to lowest. Each point passes its accumulated contribution to its downhill neighbour. Lower locations therefore collect contributions from the upstream points that drain into them.
Accumulation measures the contributing drainage area. River erosion also accounts for how much rainfall becomes runoff, so wetter drainage areas supply more water.
A point becomes a river channel when its accumulated contribution reaches a threshold. This threshold is adjusted for map size so smaller maps can still produce streams.

Lake Evaporation and Runoff:
- Lake evaporation is estimated at 700 millimetres per year at 8°C. It increases by approximately 7% for every additional degree of warming and decreases in colder conditions.
Not all rainfall reaches rivers. Some evaporates or is used by plants.
The simulator uses Fu’s form of the Budyko curve, with a parameter of 2.6, to divide annual rainfall between evaporation and runoff. The division depends on evaporative demand relative to rainfall.
Wet climates send a larger share of rainfall into rivers, while dry climates can lose nearly all of it to evaporation.

Lake Size and Overflow:
- A lake grows until incoming river water and rain on its surface balance evaporation, or until it reaches the basin’s spill level.
If the water balance supports a lake larger than the basin, it fills and overflows. Otherwise, it remains a closed lake below the spill level.
The calculation accounts for the land submerged by the lake, because that area no longer contributes land runoff.

River Width and Mountain Coverage:
- Larger accumulated flows produce wider rivers. Width grows logarithmically, so large rivers widen gradually instead of expanding in direct proportion to their upstream contributions.
The simulator finds each point’s distance from the nearest channel. Nearby points can become wet if they fall within the channel’s calculated width and are no more than 1.15 height units above the nearest channel location.
This limits water coverage on elevated banks.
The simulator also identifies high terrain using the 70th elevation percentile. It limits wet coverage within that group to 25%, keeping the lower wet locations when the limit is exceeded.
These are visual placement rules rather than a complete flooding model.

River Erosion:
- Rivers cut into the terrain faster where flow is greater and the river bed is steeper.
The erosion rate follows the stream power law: it increases with the square root of runoff-weighted drainage area and directly with slope. The base erosion coefficient is 0.000002 per year.
Vegetation reduces this coefficient by up to 70% at full cover, protecting the ground beneath it.
The solver works upstream from river mouths, using each downstream neighbour’s newly calculated height. This implicit method keeps long steps, including 10,000-year steps, stable.

Sediment Transport and Deposition:
- Material removed by river erosion is carried downstream as sediment.
At each point, a fraction settles out. This fraction is half the grid-cell area divided by the contributing drainage area, limited to a maximum of one.
Small streams therefore deposit a larger share of their sediment locally, while larger rivers carry it farther downstream.
Lakes trap sediment until they fill, allowing deltas and deposits to build up. Sediment reaching the map edge is recorded as washed off.
Without uplift, the material remaining on the map plus the material washed off should stay constant.

Plant Growth and Carrying Capacity:
- Vegetation cover ranges from zero for bare ground to one for full cover.
Plants grow using a logistic model, approaching the maximum cover that local conditions can support. If conditions worsen and this maximum falls below existing cover, vegetation decreases toward it.
The calculation uses the exact logistic solution so it can handle both short and long simulation steps.
The base growth rate is 0.15 per year. The light sensor scales this rate from 0.3 times the base rate in darkness to 1.7 times in bright conditions.
The maximum supported cover combines limits from annual average temperature, rainfall, and slope. Each limit ranges from zero to one, and the limits are multiplied together.
The temperature limit is zero at or below −4°C and reaches one at 2°C. The rainfall limit is zero at or below 150 millimetres per year and reaches one at 800 millimetres. The slope limit allows full cover up to 35° and falls to zero at 55°.
If any limit is zero, the location cannot support vegetation.

Plant Spreading and Fire:
- Plants spread into nearby ground using diffusion toward neighbouring vegetation cover, with a spreading coefficient of 300 square metres per year.
Each spreading update moves cover no more than 25% of the way toward the neighbouring average. A minimum 1% seed cover is maintained where growth is possible, allowing burned areas to recover from within as well as from their edges.
The flame sensor or B key halves plant cover within a circle whose radius is one tenth of the map width each time a burn occurs.
Reduced plant cover weakens protection against river erosion until vegetation grows back.

Terrain Rendering:
- The terrain mesh places grid points across a normalized horizontal area and converts their heights into vertical positions. The display scale then stretches this mesh to its visible size.
Each square between neighbouring grid points is divided into two triangles, allowing the graphics engine to draw the surface.
The renderer estimates slopes in both horizontal directions and uses them to calculate surface normals. These describe the direction each part of the terrain faces and allow lighting to respond to its shape.
Triangle connections and texture coordinates are created once. Later updates reuse the mesh and replace its heights and normals.

Water Rendering and Animation:
- Each wet location receives a small surface made from two triangles. Neighbouring surfaces overlap slightly to reduce visible gaps.
The corners sample the terrain between grid points so the water follows the landscape. A small vertical offset raises it above the ground to reduce flickering.
When the terrain changes, the water moves vertically to follow it. River and lake placement also depends on the drainage and lake-balance calculations described above.
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


River Network and Steady-State Checks:
- Hack’s law compares river length with the area draining into it. The simulator measures these values and fits a line on a logarithmic graph. Its slope is the scaling exponent, which is commonly around 0.5 to 0.6 for real rivers.
The planning document reports an exponent of 0.56 for the real-world map after one million simulated years. For a noise map, it reports an increase from 0.37 to 0.48 over five million years. This exponent is measured from the results rather than imposed on the model.
A separate steady-state check compares river erosion with tectonic uplift. Over a sufficiently long run, erosion should approach the rate at which uplift raises the terrain.
The planning document reports an erosion-to-uplift ratio of 0.97 after forty million simulated years, where one represents exact balance.


