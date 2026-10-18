# MathHacks2.0-TempName-

Achievements/Stuff we did:
- Replaced Ursina's point by point mesh builder with a NumPy version that calculates the whole grid at once, instead of for loops, and hands it to the GPU in a single block instead of thousands of separate objects, making rebuilds around 40x faster. Since only the heights change, we only build the triangles and texture maps once, at the start.
  
  For libraries: python -m pip install -r requirements.txt

How the Simulator’s Calculations Work:
- The simulator represents terrain as a grid of height values. Each point initially has a value between 0 and 255, with bigger values showing higher ground. Calculations update the height, estimate climate and rainfall, grow vegetation, measure changes, and generate rivers and lakes.
  
Height and Elevation:
- The simulator converts heightmap values into elevations using the minimum and maximum elevations specified in the settings.
With the current range of 0 to 1500 meters, a heightmap value of 0 represents sea level, while 255 represents 1500 meters. Values between these limits are converted proportionally. This elevation conversion is used to estimate temperature at different heights. The displayed size of the terrain is controlled separately and does not determine its real elevation.

**Calculation:**

```math
H = H_{\min} + \frac{h}{255}(H_{\max}-H_{\min})
```

Here $`h`$ is a heightmap value and $`H`$ is elevation in metres. With $`H_{\min}=0`$ and $`H_{\max}=1500`$, a value of $`h=128`$ gives $`H=128\times1500/255=752.94`$ m. One height unit represents $`1500/255=5.88235`$ m.

For the physical equations below, use elevation $`H`$ in metres, horizontal grid spacing $`\Delta x`$ in metres, and step duration $`\Delta t`$ in years. Convert a calculated elevation change back to heightmap units using $`\Delta h=255\Delta H/(H_{\max}-H_{\min})`$.

Simulation Time:
- Simulation steps can represent days, seasons, years, or longer intervals. A season is treated as 91.25 days, and a year contains exactly 365 days.
The simulator tracks elapsed time by adding the duration of every completed step. It uses this total to determine the displayed year, day, and season.
The speed settings control how many simulation steps run during each frame. Increasing the speed makes simulated time pass faster on screen without changing the duration represented by an individual step.
When the user returns to an earlier step, the simulator displays a stored copy of the terrain. Continuing from that point removes the later steps and starts a new continuation.

**Calculation:**

```math
t_{\text{elapsed}}=\sum_k d_k,\qquad \Delta t_{\text{years}}=\frac{d_k}{365}
```

Here $`d_k`$ is the length of step $`k`$ in days. One day is $`1/365=0.00273973`$ years; one season is $`91.25/365=0.25`$ years. Two years and one season total $`365+365+91.25=821.25`$ days, or $`2.25`$ years.

Soil Creep:
- Soil creep gradually smooths the terrain.
For each grid point, the simulator finds the average height of its four direct neighbours. It then moves the point’s height partway toward that average. High points become lower, while depressions become higher.
The amount of change depends on the diffusion coefficient, the duration of the simulation step, and the distance between grid points. The coefficient is 0.005 square metres per year.
Long steps are divided into smaller internal updates when needed to keep the calculation stable. The stability limit depends on grid spacing and the diffusion coefficient.
At the boundaries, the simulator repeats the nearest edge height when a neighbour would fall outside the map. This prevents material from being transferred beyond the terrain.
The calculation redistributes height across the grid and should preserve the total height sum, apart from small rounding differences.

**Calculation:**

```math
\frac{\partial H}{\partial t}=D\nabla^2H,\qquad D=0.005\ \mathrm{m^2/yr}
```

```math
H_i^{\mathrm{new}}=H_i+\alpha\left(H_N+H_S+H_E+H_W-4H_i\right),\qquad
\alpha=\frac{D\Delta t}{\Delta x^2}
```

The four neighbour heights are $`H_N,H_S,H_E,H_W`$. Stability requires $`4\alpha\leq1`$. A sufficient number of equal substeps is $`n=\max(1,\lceil4D\Delta t/\Delta x^2\rceil)`$, with each substep lasting $`\Delta t/n`$.

**Example:** For $`\Delta x=10`$ m and $`\Delta t=1000`$ years, $`\alpha=0.005\times1000/100=0.05`$. If a point is at 100 m and all four neighbours are at 90 m, its new height is $`100+0.05(360-400)=98`$ m. The step is stable because $`4\alpha=0.2`$. A 10,000-year step on the same grid needs at least $`\lceil2\rceil=2`$ substeps.

Tectonic Uplift:
- Plate movement raises the terrain in a dome-shaped pattern. Uplift is fastest at the centre and falls to zero at the map edges.
The default maximum rate is 0.3 millimetres per year. Each step adds the local uplift rate multiplied by the step’s duration in years to the terrain height.

**Calculation:**

```math
U(x,y)=U_0\sin\left(\frac{\pi x}{L}\right)\sin\left(\frac{\pi y}{L}\right),\qquad
H^{\mathrm{new}}=H+U(x,y)\Delta t
```

Here $`x,y`$ are horizontal distances across a square map of width $`L`$, and $`U_0=0.3`$ mm/yr $`=0.0003`$ m/yr. At the centre, $`x=y=L/2`$, both sine terms equal one. Over 1000 years the centre rises $`0.0003\times1000=0.3`$ m. At an edge, one sine term is zero, so uplift is zero.

Seasonal Temperature:
- Sea-level temperature follows a smooth, repeating seasonal cycle.
The current settings use an annual average of 5°C and a seasonal variation of 15°C above or below that average. This produces temperatures ranging from approximately −10°C to 20°C before additional warming is applied.
The warmest point in the cycle is set to day 200.
For steps lasting a season or a year, the simulator calculates the average temperature across the entire interval. It does not use only the temperature at the beginning of the step. A complete year averages to the configured annual temperature plus any warming adjustment.
This is a simplified climate cycle, rather than a daily weather forecast.

**Calculation:**

```math
T_{\mathrm{sea}}(t)=T_{\mathrm{avg}}+15\cos\left(\frac{2\pi(t-200)}{365}\right)+\Delta T
```

Here $`t`$ is elapsed time in days, $`T_{\mathrm{avg}}=5`$°C, and $`\Delta T`$ is the combined sensor and manual warming adjustment. At day 200 with no adjustment, $`T_{\mathrm{sea}}=5+15=20`$°C. Half a year later, the cosine is $`-1`$, giving $`5-15=-10`$°C.

For a step beginning at day $`a`$ and lasting $`d`$ days, averaging the continuous cycle gives:

```math
\overline{T}_{\mathrm{sea}}=T_{\mathrm{avg}}+\Delta T+
\frac{15}{\omega d}\left[\sin\bigl(\omega(a+d-200)\bigr)-\sin\bigl(\omega(a-200)\bigr)\right],
\qquad \omega=\frac{2\pi}{365}
```

For $`d=365`$, the sine difference is zero, giving an annual average of $`5+\Delta T`$°C.

Temperature at Higher Elevations:
- The simulator assumes that temperature decreases by 6.5°C for every 1000 metres of elevation.
At 1500 meters, the calculated temperature is therefore 9.75°C colder than the sea-level temperature.
The simulator applies this adjustment to every point on the terrain. It then counts how many points are below 0°C and expresses that count as a percentage of the whole map.
For longer steps, this percentage uses the step’s average temperature. It does not measure how long each location remains frozen.
Temperature also determines the snow line, lake evaporation, and the temperature limit on vegetation. It does not change the soil-creep calculation.

**Calculation:**

```math
T_i=T_{\mathrm{sea}}-0.0065H_i,\qquad
\text{below-freezing percentage}=100\frac{\mathrm{count}(i:T_i<0)}{N}
```

Here $`N`$ is the number of grid points. At $`H=1500`$ m and $`T_{\mathrm{sea}}=5`$°C, $`T=5-0.0065\times1500=-4.75`$°C. If 2500 of 10,000 points are below zero, the displayed percentage is $`100\times2500/10000=25\%`$.

Snow Line and Ice:
- The snow line is the elevation where the calculated temperature reaches 0°C. It is found by dividing sea-level temperature by the temperature decrease per kilometre of elevation.
The terrain shader draws snow above this line, and lakes and rivers above it turn to ice.
If the snow line is below sea level, the whole map freezes. If it is above the highest peak, no snow is drawn.
At a sea-level temperature of 5°C, the snow line is approximately 770 metres.

**Calculation:**

```math
H_{\mathrm{snow}}=\frac{T_{\mathrm{sea}}}{0.0065}\ \mathrm{m}
```

Setting $`T_i=0`$ in the elevation-temperature equation gives this height. At 5°C, $`H_{\mathrm{snow}}=5/0.0065=769.23`$ m. At 20°C it is 3076.92 m, above a 1500 m peak. At $`-10`$°C it is $`-1538.46`$ m, so terrain at or above sea level is below freezing.

Wind-Driven Rainfall:
- Wind pushes air upward on slopes facing the wind. The rising air cools and releases moisture, giving those slopes more rain. Descending air produces drier conditions on the sheltered side, creating a rain shadow.
The calculation first smooths the terrain over 600 metres so rainfall responds to broad mountainsides.
Wind speed ranges from 2 to 20 metres per second as the wind-strength input rises from zero to one. The pendulum sensor or the Y key controls this input.
The rainfall pattern is rescaled so its average remains equal to the yearly rainfall selected in the menu. Wind redistributes rain across the map without changing that average.

**Calculation:**

```math
U=2+18b,\qquad
w_i=U\left(\cos\theta\frac{\partial H}{\partial x}+\sin\theta\frac{\partial H}{\partial y}\right)
```

Here $`b\in[0,1]`$ is wind strength, $`\theta`$ is wind direction, and the derivatives are slopes of the terrain after 600 m smoothing. The quantity $`w_i`$ estimates upward air speed. For $`b=0.5`$, $`U=11`$ m/s. With wind along a slope of 0.1, $`w=11\times0.1=1.1`$ m/s.

```math
P_i=\overline{P}\frac{s_i}{\overline{s}},\qquad
\overline{s}=\frac{1}{N}\sum_i s_i
```

Here $`s_i`$ is the local rainfall weighting and $`\overline P`$ is the menu’s annual rainfall in mm/yr. For two equally sized regions with weights 1.5 and 0.5, $`\overline s=1`$. An 800 mm/yr average therefore becomes 1200 mm/yr and 400 mm/yr, whose average remains 800 mm/yr. These weights illustrate the normalization; they are not fixed windward and sheltered factors. The PDF clips the end of the equation defining $`s_i`$, so that missing expression is not reconstructed here.

Sensor Smoothing and Calibration:
- Most sensor readings are smoothed to reduce sudden fluctuations. Each new measurement moves the stored reading 20% of the way toward the latest value. This makes the display steadier, although it also makes it respond more gradually.
The first reading is stored directly. Timestamps and wind direction are not smoothed.
Light, flame, humidity, and tilt readings are converted to a scale from zero to one using calibration endpoints. Readings outside those endpoints are limited to the nearest end of the scale.
Light and flame readings use reversed calibration because lower raw readings represent stronger detection. Humidity readings from 40 to 90 are mapped across the scale, while tilt readings from 0° to 30° determine the displayed wind strength.
The interface labels normalized humidity as “rain.” This is a demonstration input, not a measurement of rainfall. Wind strength is similarly based on tilt rather than a measured wind speed.

**Calculation:**

```math
v_{\mathrm{smooth,new}}=0.8v_{\mathrm{smooth,old}}+0.2v_{\mathrm{raw}}
```

A stored temperature of 20°C followed by a raw reading of 25°C gives $`0.8\times20+0.2\times25=21`$°C. Another raw reading of 25°C gives $`0.8\times21+0.2\times25=21.8`$°C.

```math
\mathrm{clip}_{01}(q)=\min(1,\max(0,q)),\qquad
q_{\mathrm{normal}}=\mathrm{clip}_{01}\left(\frac{v-a}{b-a}\right)
```

For reversed calibration, use $`1-q_{\mathrm{normal}}`$. Humidity 65 gives $`(65-40)/(90-40)=0.5`$. A tilt of 15° gives $`15/30=0.5`$. Humidity 100 gives 1.2 before clipping and 1 after clipping.

Sensor Temperature Changes:
-The first valid temperature reading becomes the starting reference.
Later readings are compared with that reference to determine how much warmer or colder the sensor has become. This difference shifts the simulator’s climate temperatures.
Manual keyboard adjustments are added to the sensor difference. Each Up or Down input changes the manual adjustment by 0.5°C.
Re-zeroing replaces the starting reference with the current smoothed temperature.
Light controls vegetation growth, wind affects the rainfall pattern, and the flame sensor can burn vegetation. These inputs can therefore affect terrain evolution indirectly through plant cover and runoff.

**Calculation:**

```math
\Delta T=(T_{\mathrm{sensor}}-T_{\mathrm{reference}})+0.5(n_{\mathrm{up}}-n_{\mathrm{down}})
```

If the reference is 20°C, the smoothed reading is 23°C, and Up has been pressed twice, $`\Delta T=(23-20)+0.5\times2=4`$°C. The annual sea-level average becomes $`5+4=9`$°C. Re-zeroing at 23°C resets the sensor contribution to zero while retaining any manual adjustment.

Percentage of Land Changed:
- The simulator compares each current height with its original height.
A point counts as changed when the difference is greater than one height unit. The number of changed points is divided by the total number of points and expressed as a percentage.
With the current elevation range, one height unit represents approximately 5.88 metres.
This measurement shows how much of the grid has crossed the change threshold. It does not describe the average size of those changes.

**Calculation:**

```math
\Delta h_i=h_i-h_{i,0},\qquad
\text{land changed}=100\frac{\mathrm{count}(i:|\Delta h_i|>1)}{N}
```

If 300 of 1000 points differ from their original height by more than one unit, the result is $`100\times300/1000=30\%`$. A difference of exactly one unit is excluded.

Percentage of Soil Moved:
- The simulator adds up the height lost at points that are now lower than their original positions. It compares this total with the sum of the original terrain heights.
Height gains are excluded so the calculation does not count both a loss and its corresponding deposit.
This describes net height loss relative to the starting terrain. It does not track every movement during intermediate steps. Material could move several times without all of that movement appearing in the final percentage.
The result is a height-based indicator. It is not a direct measurement of soil mass or volume.

**Calculation:**

```math
\text{soil moved}=100\frac{\sum_i\max(h_{i,0}-h_i,0)}{\sum_i h_{i,0}}
```

For original heights $`(10,20,30)`$ and current heights $`(8,21,31)`$, the losses are $`(2,0,0)`$ and the original total is 60. The result is $`100\times2/60=3.33\%`$. Height gains are excluded from the numerator.

Total Soil and Roughness:
- The displayed total soil value is the sum of all terrain heights. Under soil creep alone, this should remain approximately constant because the calculation redistributes material within the grid. Uplift adds material, while sediment leaving the map reduces it.
Converting this value into physical soil volume or mass would require additional information, including the area represented by each grid point.
Roughness is calculated using the standard deviation of the terrain heights. It measures how spread out the elevations are around their average.
A larger value indicates greater overall elevation variation. A smaller value indicates a more level landscape. This measurement does not directly describe local steepness or small surface details.

**Calculation:**

```math
S=\sum_i h_i,\qquad \overline h=\frac{S}{N},\qquad
\sigma_h=\sqrt{\frac{1}{N}\sum_i(h_i-\overline h)^2}
```

For heights $`(10,20,30)`$, $`S=60`$, $`\overline h=20`$, and $`\sigma_h=\sqrt{(100+0+100)/3}=8.165`$ height units. This is about $`8.165\times1500/255=48.03`$ m of elevation standard deviation under the current conversion.

Likelihood Score:
- The simulator tests how sensitive its result is to small changes in its assumptions.
It repeats the recorded simulation twenty times. Each alternative run independently adjusts starting heights by up to one height unit and varies the process rates within their configured uncertainty ranges. These include soil creep by up to 80%, river erosion by up to 70%, and uplift by up to 50% in either direction.
The alternative runs use the same recorded history as the main simulation.
The score considers points where the main terrain changed by more than two height units, approximately 12 metres with the current elevation range. It compares the amount of change in each alternative run with the main result and counts agreement within a 25% tolerance.
The displayed score averages that agreement across the twenty runs.
A high score means the result remains similar under the tested variations. It does not mean there is that probability that the real landscape will develop that way.

**Calculation:**

```math
M=\{i:|\Delta h_i|>2\},\qquad
\mathcal L=\frac{100}{20}\sum_{r=1}^{20}
\frac{\mathrm{count}(i\in M:|\Delta h_i^{(r)}-\Delta h_i|\leq\tau_i)}{|M|}
```

Here $`\Delta h_i`$ is the main run’s height change, $`\Delta h_i^{(r)}`$ is the alternative run’s change, and $`\tau_i`$ is the agreement tolerance. The PDF describes agreement within 25%, but clips the full tolerance expression. Consequently, $`\tau_i`$ remains explicit rather than inventing the missing absolute-tolerance rule. The equation requires at least one point in $`M`$.

**Example:** If 100 points pass the change threshold and each of the twenty runs agrees at 85 of those points, $`\mathcal L=(100/20)\times20\times(85/100)=85\%`$.

The stated rate variations correspond to a soil-creep coefficient from $`0.005(1-0.8)=0.001`$ to $`0.005(1+0.8)=0.009`$ m²/yr; a river coefficient from $`0.6\times10^{-6}`$ to $`3.4\times10^{-6}`$ yr⁻¹; and maximum uplift from 0.15 to 0.45 mm/yr. These are parameter ranges for the alternative runs.

Uncertainty Map: 
- The uncertainty map measures how much the alternative simulations disagree at each location.
At every grid point, the simulator calculates the standard deviation of the alternative final heights. Higher values indicate greater disagreement, while lower values indicate more consistent results.
This uncertainty reflects the starting-height and process-rate variations included in the calculation. It does not account for every possible source of error.

**Calculation:**

```math
\overline h_i=\frac{1}{20}\sum_{r=1}^{20}h_i^{(r)},\qquad
\sigma_i=\sqrt{\frac{1}{20}\sum_{r=1}^{20}\left(h_i^{(r)}-\overline h_i\right)^2}
```

If ten runs finish at 99 units and ten at 101 units at one location, the mean is 100 and the uncertainty is $`\sqrt{(10\times1+10\times1)/20}=1`$ height unit, about 5.88 m.

River Placement:
- The river system fills depressions to their lowest spill level before calculating drainage. It works inward from the map edges, processing the lowest unvisited point first.
This produces a surface on which enclosed hollows can drain toward an outlet. The difference between this filled surface and the ground identifies potential lake basins.
Each point checks its eight surrounding neighbours, including diagonals, and selects the lowest downhill receiver on the filled surface.
This method chooses the lowest neighbouring elevation rather than the steepest slope after accounting for diagonal distance.

**Calculation:**

```math
H_i^{\mathrm{filled}}=\max\left(H_i,\min_{p:i\to\mathrm{edge}}\max_{j\in p}H_j\right)
```

For each possible route $`p`$ from a point to the map edge, find the highest elevation along that route. The smallest of these barriers sets the spill elevation. A hollow floor at 100 m with a lowest escape barrier at 120 m has a filled elevation of 120 m and a potential water depth of $`120-100=20`$ m. Its actual lake level also depends on the water balance.

```math
r(i)=\mathrm{arg\,min}_{j\in\mathcal N_8(i),\ H_j^{\mathrm{filled}}<H_i^{\mathrm{filled}}}H_j^{\mathrm{filled}}
```

The receiver $`r(i)`$ is the lowest of the eight neighbours that are lower than the point on the filled surface. This expression describes strictly downhill selection; routing across equal-height flats needs a separate tie-handling rule.

River Flow Accumulation:
- The simulator processes points from highest to lowest. Each point passes its accumulated contribution to its downhill neighbour. Lower locations therefore collect contributions from the upstream points that drain into them.
Accumulation measures the contributing drainage area. River erosion also accounts for how much rainfall becomes runoff, so wetter drainage areas supply more water.
A point becomes a river channel when its accumulated contribution reaches a threshold. This threshold is adjusted for map size so smaller maps can still produce streams.

**Calculation:**

```math
A_i=\Delta x^2+\sum_{j:r(j)=i}A_j
```

For a uniform grid, each point initially contributes its cell area. Process upstream points before their receivers. With $`\Delta x=10`$ m, each cell contributes 100 m². A receiver with three upstream cells and its own cell drains $`4\times100=400`$ m². In cell-count units, that accumulation is four. Runoff-weighted accumulation additionally weights the contributions by their local runoff.

Lake Evaporation and Runoff:
- Lake evaporation is estimated at 700 millimetres per year at 8°C. It increases by approximately 7% for every additional degree of warming and decreases in colder conditions.
Not all rainfall reaches rivers. Some evaporates or is used by plants.
The simulator uses Fu’s form of the Budyko curve, with a parameter of 2.6, to divide annual rainfall between evaporation and runoff. The division depends on evaporative demand relative to rainfall.
Wet climates send a larger share of rainfall into rivers, while dry climates can lose nearly all of it to evaporation.

**Calculation:**

```math
E_{\mathrm{lake}}=700\times1.07^{T-8}\quad\mathrm{mm/yr}
```

Here $`T`$ is the temperature in °C used for the evaporation estimate. At 0°C, $`E_{\mathrm{lake}}=700\times1.07^{-8}=407.41`$ mm/yr. At 25°C, it is $`700\times1.07^{17}=2211.17`$ mm/yr.

```math
\frac{ET}{P}=1+\frac{E}{P}-\left[1+\left(\frac{E}{P}\right)^{2.6}\right]^{1/2.6},\qquad
R=P-ET
```

Here $`P>0`$ is annual rainfall, $`E`$ is potential evaporation, $`ET`$ is actual evaporative loss including plant water use, and $`R`$ is runoff, all in mm/yr. At zero rainfall the available rainfall runoff is zero, avoiding division by zero.

**Wet example:** For $`P=3000`$ and $`E=500`$ mm/yr, $`ET=489.09`$ and $`R=2510.91`$ mm/yr. **Dry example:** For $`P=200`$ and $`E=1500`$ mm/yr, $`ET=196.94`$ and $`R=3.06`$ mm/yr.

Lake Size and Overflow:
- A lake grows until incoming river water and rain on its surface balance evaporation, or until it reaches the basin’s spill level.
If the water balance supports a lake larger than the basin, it fills and overflows. Otherwise, it remains a closed lake below the spill level.
The calculation accounts for the land submerged by the lake, because that area no longer contributes land runoff.

**Calculation:**

```math
I+PA_{\mathrm{lake}}=E_{\mathrm{lake}}A_{\mathrm{lake}}
```

This is the balance when $`I`$ is the actual river inflow at the current lake size. If $`I_0`$ instead denotes inflow before land is submerged and $`R`$ is runoff per unit land area, use $`I=I_0-RA_{\mathrm{lake}}`$:

```math
A_{\mathrm{lake}}=\frac{I_0}{E_{\mathrm{lake}}-P+R}
```

Use inflow in m³/yr and rainfall, evaporation, and runoff in m/yr, giving lake area in m². The finite-area expression applies when its denominator is positive; compare the result with the area available below the spill level.

**Example:** With $`I_0=100000`$ m³/yr, $`E_{\mathrm{lake}}=1.2`$ m/yr, $`P=0.4`$ m/yr, and $`R=0.2`$ m/yr, the equilibrium area is $`100000/(1.2-0.4+0.2)=100000`$ m². If the basin can hold only 60000 m² below its outlet, the lake fills to the outlet and overflows.

River Width and Mountain Coverage:
- Larger accumulated flows produce wider rivers. Width grows logarithmically, so large rivers widen gradually instead of expanding in direct proportion to their upstream contributions.
The simulator finds each point’s distance from the nearest channel. Nearby points can become wet if they fall within the channel’s calculated width and are no more than 1.15 height units above the nearest channel location.
This limits water coverage on elevated banks.
The simulator also identifies high terrain using the 70th elevation percentile. It limits wet coverage within that group to 25%, keeping the lower wet locations when the limit is exceeded.
These are visual placement rules rather than a complete flooding model.

**Numerical placement rules:** A candidate location must be within its channel’s calculated width and satisfy $`h_i-h_{\mathrm{channel}}\leq1.15`$ height units. Under the current elevation conversion, this height difference is $`1.15\times1500/255=6.765`$ m. If the high-terrain group contains 3000 grid points, a 25% cap allows at most $`0.25\times3000=750`$ wet points in that group. The supplied PDF does not specify the logarithmic width constants, so no numerical width equation is inferred.

River Erosion:
- Rivers cut into the terrain faster where flow is greater and the river bed is steeper.
The erosion rate follows the stream power law: it increases with the square root of runoff-weighted drainage area and directly with slope. The base erosion coefficient is 0.000002 per year.
Vegetation reduces this coefficient by up to 70% at full cover, protecting the ground beneath it.
The solver works upstream from river mouths, using each downstream neighbour’s newly calculated height. This implicit method keeps long steps, including 10,000-year steps, stable.

**Calculation:**

```math
E_i=K_{\mathrm{eff},i}Q_i^{0.5}S_i,\qquad
K_{\mathrm{eff},i}=K_0(1-0.7V_i),\qquad K_0=2\times10^{-6}\ \mathrm{yr^{-1}}
```

Here $`Q_i`$ is runoff-weighted contributing area in the model’s area convention, $`S_i`$ is downstream slope, $`V_i\in[0,1]`$ is plant cover, and $`E_i`$ is incision rate in m/yr. With area in m², its square root is in metres.

**Example:** Without plants, for $`Q=10^6`$ m² and $`S=0.1`$, $`E=2\times10^{-6}\times1000\times0.1=0.0002`$ m/yr, or 0.2 mm/yr. At full cover, $`K_{\mathrm{eff}}=0.3K_0`$, reducing the rate to 0.06 mm/yr under the same flow and slope.

The implicit height update is:

```math
F_i=\frac{K_{\mathrm{eff},i}\Delta t\sqrt{Q_i}}{\Delta d_i},\qquad
H_i^{\mathrm{new}}=\frac{H_i+F_iH_{r(i)}^{\mathrm{new}}}{1+F_i}
```

Here $`\Delta d_i`$ is distance to the downstream receiver. If $`K_{\mathrm{eff}}=2\times10^{-6}`$ yr⁻¹, $`\Delta t=1000`$ years, $`Q=10^6`$ m², and $`\Delta d=100`$ m, then $`F=0.02`$. For $`H_i=100`$ m and downstream updated height 90 m, $`H_i^{\mathrm{new}}=(100+0.02\times90)/1.02=99.80392`$ m. This is an example of the implicit update, not a constant-rate extrapolation.

Sediment Transport and Deposition:
- Material removed by river erosion is carried downstream as sediment.
At each point, a fraction settles out. This fraction is half the grid-cell area divided by the contributing drainage area, limited to a maximum of one.
Small streams therefore deposit a larger share of their sediment locally, while larger rivers carry it farther downstream.
Lakes trap sediment until they fill, allowing deltas and deposits to build up. Sediment reaching the map edge is recorded as washed off.
Without uplift, the material remaining on the map plus the material washed off should stay constant.

**Calculation:**

```math
f_i=\min\left(1,\frac{G\Delta x^2}{A_i}\right),\qquad
G=0.5,\qquad D_i=f_iQ_{s,i}
```

Here $`A_i`$ is drainage area, $`Q_{s,i}`$ is sediment arriving during the step, and $`D_i`$ is the amount deposited, in the same units as $`Q_{s,i}`$. The remainder $`(1-f_i)Q_{s,i}`$ continues downstream, with locally eroded material added to the transported sediment.

**Example:** With $`\Delta x=100`$ m and $`A=1000000`$ m², $`f=0.5\times10000/1000000=0.005`$. From 100 m³ of incoming sediment, 0.5 m³ settles and 99.5 m³ continues. Spread over the 10000 m² cell, that deposit raises it by $`0.5/10000=0.00005`$ m. Accounting for uplift separately, material conservation is $`V_{\mathrm{terrain,new}}+V_{\mathrm{exported}}=V_{\mathrm{terrain,initial}}+V_{\mathrm{uplift}}`$.

Plant Growth and Carrying Capacity:
- Vegetation cover ranges from zero for bare ground to one for full cover.
Plants grow using a logistic model, approaching the maximum cover that local conditions can support. If conditions worsen and this maximum falls below existing cover, vegetation decreases toward it.
The calculation uses the exact logistic solution so it can handle both short and long simulation steps.
The base growth rate is 0.15 per year. The light sensor scales this rate from 0.3 times the base rate in darkness to 1.7 times in bright conditions.
The maximum supported cover combines limits from annual average temperature, rainfall, and slope. Each limit ranges from zero to one, and the limits are multiplied together.
The temperature limit is zero at or below −4°C and reaches one at 2°C. The rainfall limit is zero at or below 150 millimetres per year and reaches one at 800 millimetres. The slope limit allows full cover up to 35° and falls to zero at 55°.
If any limit is zero, the location cannot support vegetation.

**Calculation:**

```math
C=\mathrm{clip}_{01}\left(\frac{T_{\mathrm{annual}}+4}{6}\right)
\mathrm{clip}_{01}\left(\frac{P-150}{650}\right)
\mathrm{clip}_{01}\left(\frac{55-\beta}{20}\right)
```

Here $`C`$ is carrying capacity, $`T_{\mathrm{annual}}`$ is local annual mean temperature in °C, $`P`$ is annual rainfall in mm/yr, and $`\beta`$ is slope in degrees. At $`T=-1`$°C, $`P=475`$ mm/yr, and $`\beta=45`$°, the factors are each 0.5, giving $`C=0.5^3=0.125`$, or 12.5% cover.

```math
\frac{dV}{dt}=rV\left(1-\frac{V}{C}\right),\qquad
V(t)=\frac{C}{1+\frac{C-V_0}{V_0}e^{-rt}}
```

Here $`V_0`$ is the starting cover and $`r=0.15m_{\mathrm{light}}`$ yr⁻¹. The light multiplier ranges from 0.3 to 1.7, so $`r`$ ranges from 0.045 to 0.255 yr⁻¹. The displayed exact solution assumes positive $`C`$ and $`V_0`$; zero-capacity and seed-establishment cases need separate handling.

**Example:** For $`C=0.8`$, $`V_0=0.1`$, $`r=0.15`$ yr⁻¹, and $`t=10`$ years, $`V=0.8/(1+7e^{-1.5})=0.31227`$, or 31.23% cover before spreading and any fire.

Plant Spreading and Fire:
- Plants spread into nearby ground using diffusion toward neighbouring vegetation cover, with a spreading coefficient of 300 square metres per year.
Each spreading update moves cover no more than 25% of the way toward the neighbouring average. A minimum 1% seed cover is maintained where growth is possible, allowing burned areas to recover from within as well as from their edges.
The flame sensor or B key halves plant cover within a circle whose radius is one tenth of the map width each time a burn occurs.
Reduced plant cover weakens protection against river erosion until vegetation grows back.

**Calculation:**

```math
V_i^{\mathrm{new}}=V_i+s(\overline V_{\mathrm{neighbours}}-V_i),\qquad
s=\min\left(0.25,\frac{300\Delta t}{\Delta x^2}\right)
```

For $`\Delta x=100`$ m and $`\Delta t=1`$ year, $`s=0.03`$. If a point has $`V_i=0.1`$ and neighbouring mean cover 0.5, spreading gives $`V_i^{\mathrm{new}}=0.1+0.03(0.5-0.1)=0.112`$. For a ten-year step, the uncapped value is 0.3 and the applied value is 0.25.

The planning document compares growth and spreading to the Fisher–KPP model, whose continuous spreading-front estimate is $`c\approx2\sqrt{rD_v}`$. At $`r=0.15`$ yr⁻¹ and $`D_v=300`$ m²/yr, $`c\approx2\sqrt{45}=13.42`$ m/yr. This is a continuous-model comparison, not an exact speed guarantee for the capped neighbour update.

```math
V_{\mathrm{after\ burn}}=0.5V_{\mathrm{before\ burn}},\qquad R_{\mathrm{burn}}=0.1L
```

A 1000 m wide map has a burn radius of 100 m. Cover of 0.8 becomes 0.4 after one burn and 0.2 after a second burn without regrowth. At cover 0.8 the erosion multiplier is $`1-0.7\times0.8=0.44`$; after the first burn it is $`1-0.7\times0.4=0.72`$. With other factors fixed, erosion increases by $`0.72/0.44=1.636`$, approximately 64%.

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

**Calculation:**

```math
L_{\mathrm{river}}=cA^{b},\qquad
\log L_{\mathrm{river}}=\log c+b\log A
```

The fitted slope $`b`$ is Hack’s exponent. The PDF uses the symbol $`h`$ for this exponent; $`b`$ is used here to distinguish it from heightmap values. If drainage area increases fourfold and $`b=0.56`$, length increases by $`4^{0.56}=2.173`$, about 2.17 times.

At steady state, uplift rate and incision rate balance:

```math
U=K_{\mathrm{eff}}\sqrt Q\,S,\qquad
S=\frac{U}{K_{\mathrm{eff}}\sqrt Q}
```

For $`U=0.0003`$ m/yr, $`K_{\mathrm{eff}}=2\times10^{-6}`$ yr⁻¹, and $`Q=10^6`$ m², the equilibrium slope is $`0.0003/0.002=0.15`$. An erosion-to-uplift ratio of 0.97 represents a $`100(1-0.97)=3\%`$ shortfall relative to exact balance.


Created using textures from ambientCG.com,
licensed under the Creative Commons CC0 1.0 Universal License.
