# MathHacks2.0-TempName-

<<<<<<< HEAD
Achievements/Stuff we did:
=======
## Achievements/Stuff we did

>>>>>>> 6f462d55238ad6b8f075802de15a3d4c03da83a4
- Replaced Ursina's point by point mesh builder with a NumPy version that calculates the whole grid at once, instead of for loops, and hands it to the GPU in a single block instead of thousands of separate objects, making rebuilds around 40x faster. Since only the heights change, we only build the triangles and texture maps once, at the start.
  
  For libraries: python -m pip install -r requirements.txt

<<<<<<< HEAD
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
The speed keys (1, 2, 3) set how long a whole run takes to watch: 15, 5 or 1 seconds, however many steps it has. In nonstop mode (0 in the steps box) they give 2, 10 or 40 steps per second. Faster speeds make simulated time pass faster on screen without changing the duration represented by an individual step.
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

The four neighbour heights are $`H_N,H_S,H_E,H_W`$. Stability requires $`4\alpha\leq1`$; the code keeps $`4\alpha\leq0.5`$ in each substep for a safety margin, so it uses $`n=\max(1,\lceil8D\Delta t/\Delta x^2\rceil)`$ equal substeps, each lasting $`\Delta t/n`$.

**Example:** For $`\Delta x=10`$ m and $`\Delta t=1000`$ years, $`\alpha=0.005\times1000/100=0.05`$. If a point is at 100 m and all four neighbours are at 90 m, its new height is $`100+0.05(360-400)=98`$ m. The step is stable because $`4\alpha=0.2`$. A 10,000-year step on the same grid has $`4\alpha=2`$, so the code splits it into $`\lceil2/0.5\rceil=4`$ substeps.

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
\text{below-freezing percentage}=100\frac{\mathrm{count}(i:T_i\lt 0)}{N}
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
Wind speed ranges from 2 to 20 metres per second as the wind-strength input rises from zero to one. The joystick or the Y key controls this input.
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

Here $`s_i`$ is the local rainfall weighting and $`\overline P`$ is the menu’s annual rainfall in mm/yr. For two equally sized regions with weights 1.5 and 0.5, $`\overline s=1`$. An 800 mm/yr average therefore becomes 1200 mm/yr and 400 mm/yr, whose average remains 800 mm/yr. These weights illustrate the normalization. The weights themselves come from the upward air speed:

```math
s_i=\max\left(0.15,\ 1+0.25\,(0.5+b)\,\frac{w_i}{\overline{|w|}}\right)
```

Slopes where air rises ($`w_i \gt 0`$) get weights above 1, sheltered slopes get less, and no point drops below 15% of the average. Stronger wind ($`b`$) makes the contrast bigger.

Sensor Smoothing and Zero Point:
- Most sensor readings are smoothed to reduce sudden fluctuations. Each new measurement moves the stored reading 20% of the way toward the latest value. This makes the display steadier, although it also makes it respond more gradually.
The first reading is stored directly. Timestamps and wind direction are not smoothed.
When the simulation starts (and when R or Z is pressed), every sensor's current reading is saved as its zero point. The simulator reacts to changes from that zero point, so the room's own temperature, humidity and light don't matter.
Humidity above the zero point increases the rain, the light sensor speeds up or slows down plant growth, and the flame sensor counts as fire once its reading has moved 30% of the way from its zero point toward the far end of its range. This works whichever direction the flame module reads.
The joystick sends its push distance as 0 to 30, which becomes a wind strength from 0 to 1, and its push direction as the wind direction.

**Calculation:**

```math
v_{\mathrm{smooth,new}}=0.8v_{\mathrm{smooth,old}}+0.2v_{\mathrm{raw}}
```

A stored temperature of 20°C followed by a raw reading of 25°C gives $`0.8\times20+0.2\times25=21`$°C. Another raw reading of 25°C gives $`0.8\times21+0.2\times25=21.8`$°C.

```math
\text{rain multiplier}=\mathrm{clip}\left(1+\frac{\mathrm{sign}(\Delta RH)\max(0,|\Delta RH|-1)}{3},\ 0.25,\ 3\right)
```

Here $`\Delta RH`$ is the humidity change from the zero point in %. Changes of 1% or less are ignored because the DHT11 only reads whole percentages. Breathing on the sensor for $`\Delta RH=+4`$% gives $`1+3/3=2`$, doubling the menu's rainfall; $`+7`$% reaches the maximum of 3.

```math
\text{fire level}=\frac{|v-v_0|}{\text{distance from }v_0\text{ to the far end of }0\ldots4095},\qquad \text{fire if level}\gt 0.3
```

A flame module resting at $`v_0=80`$ that rises to 1500 near a flame gives $`(1500-80)/(4095-80)=0.35`$, so it counts as fire.

```math
b=\frac{\text{joystick push}}{30},\qquad m_{\mathrm{light}}=\mathrm{clip}\left(1+2(\ell-\ell_0),\ 0.3,\ 1.7\right)
```

Here $`b`$ is wind strength and $`\ell`$ is the light reading on a 0 to 1 scale, with $`\ell_0`$ its zero point. A push of 15 gives $`b=0.5`$.

Sensor Temperature Changes:
- The temperature at the zero point is the reference.
Later readings are compared with that reference to determine how much warmer or colder the sensor has become. This difference shifts the simulator's climate temperatures.
Manual keyboard adjustments are added to the sensor difference. Each Up or Down input changes the manual adjustment by 0.5°C.
Re-zeroing (R or Z) replaces the reference with the current smoothed temperature.
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
\text{land changed}=100\frac{\mathrm{count}(i:|\Delta h_i|\gt 1)}{N}
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
It repeats the recorded simulation up to twenty times (fewer if twenty would take more than 6 seconds). Each alternative run independently adjusts starting heights by up to one height unit and varies the process rates within their configured uncertainty ranges. These include soil creep by up to 80%, river erosion by up to 70%, and uplift by up to 50% in either direction.
The alternative runs use the same recorded history as the main simulation.
The score considers points where the main terrain changed by more than two height units, approximately 12 metres with the current elevation range. It compares the amount of change in each alternative run with the main result and counts agreement within a 25% tolerance.
The displayed score averages that agreement across the runs.
A high score means the result remains similar under the tested variations. It does not mean there is that probability that the real landscape will develop that way.

**Calculation:**

```math
M=\{i:|\Delta h_i|\gt 2\},\qquad
\mathcal L=\frac{100}{R}\sum_{r=1}^{R}
\frac{\mathrm{count}(i\in M:|\Delta h_i^{(r)}-\Delta h_i|\leq\tau_i)}{|M|}
```

Here $`R`$ is the number of alternative runs, $`\Delta h_i`$ is the main run’s height change, $`\Delta h_i^{(r)}`$ is the alternative run’s change, and the agreement tolerance is $`\tau_i=\max(1,\ 0.25|\Delta h_i|)`$ height units: within 25%, but never stricter than 1 unit. If no point is in $`M`$, the score is shown as "nothing has changed enough to score yet".

**Example:** If 100 points pass the change threshold and each of $`R=20`$ runs agrees at 85 of those points, $`\mathcal L=(100/20)\times20\times(85/100)=85\%`$.

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
r(i)=\mathrm{arg\,min}_{j\in\mathcal N_8(i),\ H_j^{\mathrm{filled}}\lt H_i^{\mathrm{filled}}}H_j^{\mathrm{filled}}
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

Here $`P\gt 0`$ is annual rainfall, $`E`$ is potential evaporation, $`ET`$ is actual evaporative loss including plant water use, and $`R`$ is runoff, all in mm/yr. At zero rainfall the available rainfall runoff is zero, avoiding division by zero.

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

River and Lake Drawing:
- A point is drawn as a river when enough runoff drains through it: about 0.5 square kilometres of land at a reference runoff of 300 millimetres per year. Wetter climates and windward slopes therefore produce more rivers.
Larger flows are drawn deeper. Depth grows with the logarithm of the flow, so large rivers grow gradually instead of in direct proportion to their upstream contributions.
Lakes are hollows at least 0.3 height units deep and at least 0.1 square kilometres in area. Smaller ponds are not drawn, although water still flows through them.
Rivers that run diagonally also mark one neighbouring point, so the river is drawn as one connected line instead of separate dots.

**Calculation:**

```math
Q_{\min}=\max\left(2,\ \frac{0.5\ \mathrm{km^2}}{\Delta x^2}\right),\qquad
d_{\mathrm{river}}=0.5\left(1+\frac{\log_2\max(Q/Q_{\min},1)}{3}\right)
```

Here $`Q`$ is the runoff-weighted flow in grid points and $`d_{\mathrm{river}}`$ is the drawn depth in height units. With $`\Delta x=79`$ m, $`\Delta x^2=0.0062`$ km², so $`Q_{\min}=81`$ points. A river carrying 8 times that flow is drawn $`0.5(1+3/3)=1`$ height unit deep.

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

Growth plus spreading together is the Fisher–KPP model, whose continuous spreading-front estimate is $`c\approx2\sqrt{rD_v}`$. At $`r=0.15`$ yr⁻¹ and $`D_v=300`$ m²/yr, $`c\approx2\sqrt{45}=13.42`$ m/yr. This is a continuous-model comparison, not an exact speed guarantee for the capped neighbour update.

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
- The water is a second copy of the terrain mesh, using the same grid and the same triangles. Where there is water, its surface sits above the ground; everywhere else it sits just below the ground, so it is hidden. Because both meshes share the same triangles, river and lake edges come out smooth instead of blocky.
The water is worked out again in the background while the simulation runs, so the app does not freeze. In between, the last water surface moves up and down with the changing ground.
The blue water texture is generated using repeating mathematical waves. One pattern creates narrow bright ripple crests, while another adds changes in brightness. The texture slides over time to create the appearance of flowing water.
Water above the snow line is drawn as ice, so high lakes freeze first and, with Day or Season steps, lakes freeze in winter and thaw in spring.
This animation is visual. It does not calculate physical water velocity.

Procedural Terrain Generation:
- The procedural generator creates terrain using simplex noise.
It combines several layers of noise (octaves, chosen in the menu; 4 by default). Each successive layer has twice the sampling frequency and half the amplitude of the previous layer. Broad layers create larger features, while finer layers add smaller variations.
The frequency setting controls how much variation fits into the image. A random seed selects the terrain pattern.
The menu offers a generated map alongside the real one, with a seed, resolution (128 to 512 points across), frequency and octaves. The result is smoothed slightly and stretched so its lowest point is 0 and its highest is 255. If the noise package is not installed, a simple backup generator is used instead.

Saved Maps and Charts:
- The change map compares current heights with original heights. Red represents height loss, while blue represents height gain. Equal-sized losses and gains use comparable colour intensity.
The history chart shows how the land-changed and soil-moved percentages develop over simulated time. A separate axis displays the recorded sea-level temperature.
The uncertainty map shows where alternative simulation runs produce the greatest differences.


River Network and Steady-State Checks:
- Hack’s law compares river length with the area draining into it. The simulator measures these values and fits a line on a logarithmic graph. Its slope is the scaling exponent, which is commonly around 0.5 to 0.6 for real rivers.
Running hacks_law.py gives an exponent of 0.56 for the real-world map after one million simulated years. A noise map rises from 0.37 to 0.48 over five million years, toward the real-world range. This exponent is measured from the results rather than imposed on the model.
A separate steady-state check compares river erosion with tectonic uplift. Over a sufficiently long run, erosion should approach the rate at which uplift raises the terrain.
Our test gives an erosion-to-uplift ratio of 0.97 after forty million simulated years, where one represents exact balance.

**Calculation:**

```math
L_{\mathrm{river}}=cA^{b},\qquad
\log L_{\mathrm{river}}=\log c+b\log A
```

The fitted slope $`b`$ is Hack’s exponent (often written $`h`$; $`b`$ is used here to avoid confusion with heightmap values). If drainage area increases fourfold and $`b=0.56`$, length increases by $`4^{0.56}=2.173`$, about 2.17 times.

At steady state, uplift rate and incision rate balance:

```math
U=K_{\mathrm{eff}}\sqrt Q\,S,\qquad
S=\frac{U}{K_{\mathrm{eff}}\sqrt Q}
```

For $`U=0.0003`$ m/yr, $`K_{\mathrm{eff}}=2\times10^{-6}`$ yr⁻¹, and $`Q=10^6`$ m², the equilibrium slope is $`0.0003/0.002=0.15`$. An erosion-to-uplift ratio of 0.97 represents a $`100(1-0.97)=3\%`$ shortfall relative to exact balance.


Created using textures from ambientCG.com,
licensed under the Creative Commons CC0 1.0 Universal License.
=======
Install the required libraries:

```bash
python -m pip install -r requirements.txt
```

## How the Simulator's Calculations Work

The terrain is a grid, like a spreadsheet in which every cell stores the height of one location. The starting heightmap contains values from 0 to 255. Larger values mean higher ground.

During a simulation step, the program uses mathematical models to update the landscape. For example, soil moves between nearby locations, rivers wear away the ground, and plants grow or burn. Other calculations estimate temperature and rainfall or measure how much the terrain has changed.

The explanations below use Grade 12 ideas such as proportional relationships, trigonometric functions, exponential functions, and statistics. Each numerical example shows how to use the formula and what its answer means. These are simplified models of environmental processes.

### Reading the Formulas

| Symbol or notation | Meaning |
| --- | --- |
| $h$ | A height stored in heightmap units. |
| $H$ | An elevation in metres. |
| A subscript such as $H_i$ | The value at grid location $i$. |
| $\Delta$ | A change or interval. For example, $\Delta t$ is the length of a time step. |
| A bar, such as $\overline{H}$ | An average. |
| $\sum$ | Add the relevant values together. |
| $\min(a,b)$ or $\max(a,b)$ | Choose the smaller or larger of the two values. |
| $|x|$ | Absolute value: the size of a number without its sign. |
| $e$ | The exponential-function constant, approximately 2.71828. |

In formulas for physical terrain changes, elevation is in metres, grid spacing $\Delta x$ is in metres, and time $\Delta t$ is in years unless stated otherwise. Temperature-cycle formulas use days. Keep these units consistent when substituting values.

### Height and Elevation

**Purpose:** Convert the image's height values into elevations that can be used in calculations such as temperature at different heights.

This is a proportional relationship. First, divide a heightmap value by 255 to find its position between the lowest and highest possible values. Multiply that fraction by the elevation range, then add the minimum elevation.

```math
H=H_{\min}+\frac{h}{255}(H_{\max}-H_{\min})
```

For a minimum of 0 m and maximum of 1500 m, a heightmap value of 128 becomes:

```math
H=0+\frac{128}{255}(1500-0)=752.94\ \text{m}
```

So this location is about 753 m above sea level. Each heightmap unit represents:

```math
\frac{1500}{255}=5.88235\ \text{m}
```

To convert a calculated elevation change back into heightmap units, reverse the conversion:

```math
\Delta h=\frac{255\Delta H}{H_{\max}-H_{\min}}
```

For example, a 10 m increase corresponds to $255(10)/1500=1.7$ heightmap units. The terrain's display scale controls its visible size separately from these elevations.

### Simulation Time

**Purpose:** Keep track of how much simulated time has passed.

The simulator adds the duration of each completed step. It treats one year as 365 days and one season as 91.25 days.

```math
\text{elapsed days}=\text{step 1 days}+\text{step 2 days}+\cdots
```

```math
\text{step length in years}=\frac{\text{step length in days}}{365}
```

For two one-year steps followed by one season:

```math
365+365+91.25=821.25\ \text{days}
```

```math
\frac{821.25}{365}=2.25\ \text{years}
```

The speed setting changes how many steps run during each frame. It makes the simulation advance faster on screen without changing the time represented by each step.

Going back to an earlier step displays a saved terrain state. Continuing from that point removes the later states and creates a new continuation.

### Soil Creep

**Purpose:** Slowly smooth the landscape by moving material away from high points and into lower areas.

For each location, find the average height of its north, south, east, and west neighbours. The location then moves partway toward that average.

```math
\overline{H}_{\text{neighbours}}=\frac{H_N+H_S+H_E+H_W}{4}
```

```math
\alpha=\frac{D\Delta t}{(\Delta x)^2}
```

```math
H_{\text{new}}=H+4\alpha(\overline{H}_{\text{neighbours}}-H)
```

Here, $D=0.005$ m²/year controls how quickly the soil spreads. The factor $4\alpha$ is the fraction of the difference closed during one update.

**Example:** Suppose a point is 100 m high, all four neighbours are 90 m high, grid spacing is 10 m, and the step lasts 1000 years.

```math
\alpha=\frac{0.005(1000)}{10^2}=0.05
```

```math
H_{\text{new}}=100+4(0.05)(90-100)=98\ \text{m}
```

The point moves 20% of the way toward its neighbours' average, falling by 2 m. A low point surrounded by higher neighbours rises instead.

To keep the update stable, $4\alpha$ must be no greater than 1. Otherwise, a point could jump past its neighbours' average and cause unrealistic oscillations. Long steps are split into enough shorter updates to satisfy this limit. With the same spacing, a 10,000-year step gives $4\alpha=2$, so at least two internal updates are needed.

At the map boundary, a missing neighbour is replaced by the nearest edge height. Soil creep therefore redistributes material within the map and should preserve the total height sum, apart from rounding.

### Tectonic Uplift

**Purpose:** Represent slow upward movement of the land caused by tectonic activity.

The model uses sine functions to create a smooth uplift pattern. Uplift is greatest at the centre and zero at the edges.

```math
U(x,y)=U_0\sin\left(\frac{\pi x}{L}\right)\sin\left(\frac{\pi y}{L}\right)
```

Here, $x$ and $y$ are horizontal positions on a square map, $L$ is its width, and $U_0$ is the maximum uplift rate. The angles are in radians.

At the centre, $x=y=L/2$, so each sine term is $\sin(\pi/2)=1$. The default maximum rate is 0.3 mm/year, or 0.0003 m/year.

Height gained is rate multiplied by time:

```math
H_{\text{new}}=H+U(x,y)\Delta t
```

Over 1000 years, the centre rises by $0.0003(1000)=0.3$ m. At an edge, one sine term is zero, so that edge receives no uplift.

### Seasonal Temperature

**Purpose:** Make temperature rise and fall through a repeating yearly cycle.

A cosine function gives a smooth seasonal pattern:

```math
T_{\text{sea}}(t)=5+15\cos\left(\frac{2\pi(t-200)}{365}\right)+\Delta T
```

The vertical shift of 5°C is the annual average. The amplitude of 15°C means temperature varies 15°C above and below that average. Dividing by 365 makes the period one year, and subtracting 200 places the warmest point at day 200. The value $\Delta T$ adds the sensor and manual temperature adjustments. Use radians for the cosine.

At day 200 with no adjustment:

```math
T_{\text{sea}}=5+15\cos(0)=20^\circ\text{C}
```

Half a year later, the cosine is $-1$, so temperature is $5-15=-10$°C.

A step lasting a season or a year uses the average temperature over that interval. This avoids treating an entire year as though it had the temperature of its first day. The interval-average formula is:

```math
\overline{T}_{\text{sea}}=5+\Delta T+
\frac{15}{\omega d}\left[\sin\left(\omega(a+d-200)\right)-\sin\left(\omega(a-200)\right)\right]
```

Here, $a$ is the starting day, $d$ is the step duration in days, and $\omega=2\pi/365$. The sine difference accounts for how much of the seasonal cycle the step covers. Over exactly 365 days, the sine values match and cancel. The average is then $5+\Delta T$°C.

This models a seasonal trend rather than daily weather.

### Temperature at Higher Elevations

**Purpose:** Make higher ground colder than lower ground.

The model subtracts 6.5°C for every 1000 m of elevation, equivalent to 0.0065°C per metre.

```math
T_i=T_{\text{sea}}-0.0065H_i
```

At 1500 m with a sea-level temperature of 5°C:

```math
T_i=5-0.0065(1500)=5-9.75=-4.75^\circ\text{C}
```

The simulator also counts the locations below 0°C:

```math
\text{below-freezing percentage}=\frac{\text{number of points below }0^\circ\text{C}}{\text{total number of points}}\times100
```

If 2500 of 10,000 points are below freezing, the result is 25%. For long steps, this uses the interval's average temperature, so it does not measure how many days the ground was frozen.

Temperature affects snow, ice, evaporation, and the vegetation limit. It does not change the soil-creep formula.

### Snow Line and Ice

**Purpose:** Find the elevation where the model's temperature reaches 0°C.

Start with the elevation-temperature equation and set temperature to zero:

```math
0=T_{\text{sea}}-0.0065H_{\text{snow}}
```

Rearranging gives:

```math
H_{\text{snow}}=\frac{T_{\text{sea}}}{0.0065}
```

At a sea-level temperature of 5°C, the snow line is $5/0.0065=769.23$ m. The renderer draws snow above that line, and water above it turns to ice.

At 20°C, the line is 3076.92 m, above every point on a map whose highest peak is 1500 m. At −10°C, it is −1538.46 m, so all terrain at or above sea level is below freezing in this model.

### Wind-Driven Rainfall

**Purpose:** Put more rain on slopes facing the wind and less on sheltered slopes.

The wind-strength input $b$ ranges from 0 to 1. The model converts it into a wind speed:

```math
U=2+18b
```

An input of 0 gives 2 m/s, an input of 1 gives 20 m/s, and an input of 0.5 gives 11 m/s. The input comes from the pendulum sensor or the Y key.

The terrain is first smoothed over 600 m so broad mountainsides guide the rainfall pattern. Slope means rise divided by horizontal distance. The model combines slopes in the two map directions with wind direction:

```math
w=U(s_x\cos\theta+s_y\sin\theta)
```

Here, $s_x$ and $s_y$ are the smoothed terrain slopes, $\theta$ is wind direction, and $w$ estimates upward air speed. If wind blows directly up a slope of 0.1 at 11 m/s, then $w=11(0.1)=1.1$ m/s. Rising air encourages rain; descending air creates a rain shadow.

The model assigns each location a rainfall weight, then rescales the weights to preserve the menu's average annual rainfall:

```math
P_i=\overline{P}\frac{s_i}{\overline{s}}
```

Here, $s_i$ is a rainfall weight, $\overline{s}$ is the average weight, and $\overline{P}$ is the selected average rainfall. These weights are different from the slopes above.

For two equally sized regions with weights 1.5 and 0.5, the average weight is 1. If average rainfall is 800 mm/year, their rainfall values become 1200 and 400 mm/year. Their average is still 800 mm/year. Wind redistributes the rain rather than increasing the overall average.

The original README does not provide the complete formula that converts upward air speed into a rainfall weight. The example explains the rescaling without assuming missing constants.

### Sensor Smoothing and Calibration

**Purpose:** Reduce sudden jumps in sensor readings and convert different sensors to a common scale.

Smoothing is a weighted average. The previous smoothed reading receives an 80% weight and the latest raw measurement receives a 20% weight:

```math
v_{\text{new}}=0.8v_{\text{old}}+0.2v_{\text{raw}}
```

If the stored temperature is 20°C and the new measurement is 25°C:

```math
v_{\text{new}}=0.8(20)+0.2(25)=21^\circ\text{C}
```

Another measurement of 25°C moves it to $0.8(21)+0.2(25)=21.8$°C. The reading approaches 25°C gradually. The first valid measurement is stored directly; timestamps and wind direction are not smoothed.

Calibration converts a reading $v$ between endpoints $a$ and $b$ into a value between 0 and 1:

```math
q=\frac{v-a}{b-a}
```

Values below 0 are set to 0, and values above 1 are set to 1. This is called **clipping**. Where the formulas below say $\mathrm{clip}_{01}(q)$, they mean:

```math
\mathrm{clip}_{01}(q)=\min(1,\max(0,q))
```

Humidity uses endpoints 40 and 90. A reading of 65 becomes $(65-40)/(90-40)=0.5$. A reading of 100 gives 1.2, which is clipped to 1. Tilt uses 0° to 30°, so 15° becomes 0.5.

Light and flame use reversed calibration, $1-q$, because lower raw readings mean stronger detection. The interface labels normalized humidity as "rain," and uses tilt as wind strength. These are demonstration inputs rather than direct rainfall or wind-speed measurements.

### Sensor Temperature Changes

**Purpose:** Let changes in the sensor temperature shift the simulated climate.

The first valid temperature reading becomes the reference. Later smoothed readings are compared with it, and manual adjustments are added:

```math
\Delta T=(T_{\text{sensor}}-T_{\text{reference}})+0.5(n_{\text{up}}-n_{\text{down}})
```

Here, $n_{\text{up}}$ and $n_{\text{down}}$ count the manual Up and Down inputs. Each changes the adjustment by 0.5°C.

If the reference is 20°C, the current smoothed reading is 23°C, and Up has been pressed twice:

```math
\Delta T=(23-20)+0.5(2)=4^\circ\text{C}
```

The annual sea-level average changes from 5°C to 9°C. Re-zeroing at 23°C makes the sensor difference zero again while keeping the manual adjustment.

Other inputs affect the landscape through different processes: light changes plant growth, wind changes rainfall distribution, and flame can reduce plant cover.

### Percentage of Land Changed

**Purpose:** Measure how much of the map has changed by more than a set threshold.

Subtract each original height from its current height:

```math
\Delta h_i=h_i-h_{i,0}
```

The subscript 0 means the original value. The model counts a location as changed when $|\Delta h_i|>1$, so both increases and decreases count.

```math
\text{land changed}=\frac{\text{number of points with }|\Delta h_i|>1}{\text{total number of points}}\times100
```

If 300 out of 1000 points pass the threshold, the result is 30%. A change of exactly one unit does not count. With the 0 to 1500 m elevation range, the threshold is approximately 5.88 m.

This percentage measures the area crossing the threshold. It does not tell you the average size of the height changes.

### Percentage of Soil Moved

**Purpose:** Compare the height lost from locations with the original total height.

For each location, subtract the current height from its original height. Keep positive losses and replace negative values with zero so height gains do not enter the total.

```math
\text{loss at point }i=\max(h_{i,0}-h_i,0)
```

```math
\text{soil moved}=\frac{\text{sum of height losses}}{\text{sum of original heights}}\times100
```

Suppose original heights are 10, 20, and 30, while current heights are 8, 21, and 31. The counted losses are 2, 0, and 0. Therefore:

```math
\text{soil moved}=\frac{2}{10+20+30}\times100=3.33\%
```

Only the final difference from the starting terrain is measured. Soil that moved several times is not counted each time. This is a height-based indicator, not a direct measurement of soil mass or volume, and the ratio needs a nonzero original total.

### Total Soil and Roughness

**Purpose:** Track the total of the stored heights and describe how widely those heights vary.

The displayed total soil value adds all heightmap values. For heights 10, 20, and 30:

```math
S=10+20+30=60
```

Soil creep alone should keep this sum approximately constant. Uplift increases it, while sediment exported from the map reduces it. Converting the value into physical volume or mass would require information such as cell area and, for mass, density.

Roughness uses **population standard deviation**, a measure of spread around the average:

```math
\overline{h}=\frac{h_1+h_2+\cdots+h_N}{N}
```

```math
\sigma_h=\sqrt{\frac{(h_1-\overline{h})^2+(h_2-\overline{h})^2+\cdots+(h_N-\overline{h})^2}{N}}
```

For 10, 20, and 30, the average is 20. Subtract 20 from each height, square the differences, average them, and take the square root:

```math
\sigma_h=\sqrt{\frac{(-10)^2+0^2+10^2}{3}}=8.165
```

This is 8.165 heightmap units, equivalent to about $8.165(1500/255)=48.03$ m of elevation standard deviation. A larger value means greater overall elevation variation. It does not directly measure how steep neighbouring points are.

### Likelihood Score

**Purpose:** Test whether similar results appear when the simulation's starting conditions and rates change slightly.

The simulator repeats the recorded history 20 times with altered assumptions. Starting heights vary by up to one heightmap unit. Soil-creep rates vary by up to 80%, river-erosion rates by up to 70%, and uplift rates by up to 50% in either direction.

For example, a soil-creep coefficient of 0.005 m²/year with an 80% variation gives:

```math
D_{\min}=0.005(1-0.8)=0.001\ \text{m}^2/\text{year}
```

```math
D_{\max}=0.005(1+0.8)=0.009\ \text{m}^2/\text{year}
```

The river coefficient ranges from $0.6\times10^{-6}$ to $3.4\times10^{-6}$ per year. Maximum uplift ranges from 0.15 to 0.45 mm/year.

The comparison focuses on locations where the main simulation changed by more than two heightmap units, approximately 11.76 m under the current conversion. At those points, each alternative run's height change is compared with the main run's change using an agreement tolerance described as 25% in the source material.

```math
\text{agreement for one run}=\frac{\text{number of selected points that agree}}{\text{number of selected points}}\times100
```

```math
\text{likelihood score}=\frac{\text{sum of the 20 agreement percentages}}{20}
```

If 100 locations qualify and every alternative run agrees at 85 of them, each run has 85% agreement and the final score is 85%.

The original README does not specify the full tolerance rule, so a more detailed rule is not assumed here. There must also be at least one qualifying location for the displayed ratio to be defined.

A high score means the tested alternatives produced similar changes. It is not a probability that the real landscape will evolve that way.

### Uncertainty Map

**Purpose:** Show where the alternative simulations disagree most.

At each map location, take the 20 final heights and calculate their standard deviation. This uses the same statistical method as roughness, but compares different runs at one location rather than different locations in one run.

**Example:** At one location, ten runs finish at height 99 and ten at height 101. The average is 100. Every height differs from that average by one unit, so:

```math
\sigma=\sqrt{\frac{10(99-100)^2+10(101-100)^2}{20}}=1
```

The uncertainty there is one heightmap unit, equivalent to about 5.88 m. Higher standard deviation means more disagreement. This map reflects the variations tested, rather than every possible source of error.

### River Placement

**Purpose:** Determine where water can drain and where hollows could hold lakes.

Imagine slowly filling a hollow with water. It cannot spill out until the water reaches the lowest escape barrier. The drainage calculation finds that spill height by working inward from the map edges, processing low points first.

For a hollow with a floor at 100 m and a lowest escape barrier at 120 m:

```math
\text{potential lake depth}=120-100=20\ \text{m}
```

This filled surface helps identify potential lake basins. The actual lake level also depends on incoming water and evaporation.

For downhill flow, each point checks its eight neighbours, including diagonals, and chooses the neighbour with the lowest elevation below its own on the filled surface. That neighbour is called its **receiver**.

For example, if a point is at 120 m and eligible neighbours are at 119, 116, and 118 m, it chooses the 116 m neighbour. The rule selects the lowest neighbour, rather than calculating which direction has the steepest slope after accounting for diagonal distance. Equal-height flat areas require an additional routing rule.

### River Flow Accumulation

**Purpose:** Find how much upstream land drains through each location.

Each grid cell contributes its own area. As the simulator processes locations from high to low, each passes its accumulated area to its downstream receiver.

```math
\text{cell area}=(\Delta x)^2
```

```math
A_i=\text{cell area}+\text{total area passed in from upstream}
```

With 10 m spacing, each cell represents $10^2=100$ m². A location receiving drainage from three other cells has a total contributing area of:

```math
A=100+3(100)=400\ \text{m}^2
```

The same accumulation can be represented as a count of four cells. Large accumulated contributions identify likely river channels. The threshold is adjusted for map size so smaller maps can still show streams.

For erosion, contributions are also weighted by runoff. This allows wet upstream land to contribute more strongly than dry land. The resulting runoff-weighted area is the model's flow measure, not directly a measured river discharge in m³/s.

### Lake Evaporation and Runoff

**Purpose:** Estimate water lost to evaporation and water available to flow into rivers.

Lake evaporation follows an exponential relationship:

```math
E_{\text{lake}}=700(1.07)^{T-8}
```

Here, $T$ is the temperature used for the estimate in °C, and the result is in mm/year. At 8°C, the exponent is zero, so evaporation is 700 mm/year. Each additional degree multiplies evaporation by 1.07, a 7% increase.

At 0°C:

```math
E_{\text{lake}}=700(1.07)^{-8}=407.41\ \text{mm/year}
```

At 25°C, it is $700(1.07)^{17}=2211.17$ mm/year. The repeated multiplication makes the relationship exponential rather than linear.

Not all rainfall becomes runoff. Water can evaporate or be used by plants. The model estimates this division using Fu's form of the Budyko curve. First, calculate the ratio of potential evaporation $E$ to rainfall $P$:

```math
x=\frac{E}{P}
```

Then calculate actual evaporative loss $ET$ and runoff $R$:

```math
ET=P\left[1+x-(1+x^{2.6})^{1/2.6}\right]
```

```math
R=P-ET
```

All water-depth values use mm/year. Potential evaporation describes evaporative demand; actual evaporative loss is limited by the water available. The parameter 2.6 controls the curve's shape.

For a wet climate with $P=3000$ and $E=500$ mm/year, $x=1/6$. Substitution gives $ET=489.09$ and $R=2510.91$ mm/year, so about 84% of the rainfall becomes runoff.

For a dry climate with $P=200$ and $E=1500$ mm/year, $x=7.5$. The result is $ET=196.94$ and $R=3.06$ mm/year. Almost all rainfall is lost before becoming runoff. When rainfall is zero, available rainfall runoff is set to zero without dividing by $P$.

### Lake Size and Overflow

**Purpose:** Decide whether a lake remains below its outlet or fills and overflows.

A lake is in water balance when incoming river water plus rain falling on its surface equals evaporation from that surface:

```math
I+PA_{\text{lake}}=E_{\text{lake}}A_{\text{lake}}
```

Here, $I$ is river inflow in m³/year, $A_{\text{lake}}$ is lake area in m², and $P$ and $E_{\text{lake}}$ are in m/year. Multiplying a water depth by an area gives a water volume.

As the lake expands, it submerges land that previously supplied runoff. If $I_0$ is inflow before that land is submerged and $R$ is land runoff in m/year, the adjusted inflow is $I=I_0-RA_{\text{lake}}$. Substituting and rearranging gives:

```math
A_{\text{lake}}=\frac{I_0}{E_{\text{lake}}-P+R}
```

**Example:** Let $I_0=100000$ m³/year, $E_{\text{lake}}=1.2$ m/year, $P=0.4$ m/year, and $R=0.2$ m/year.

```math
A_{\text{lake}}=\frac{100000}{1.2-0.4+0.2}=100000\ \text{m}^2
```

That is the equilibrium area predicted by the balance. If the basin can hold only 60,000 m² of lake surface below its outlet, the lake reaches the outlet and overflows instead.

This finite-area formula requires a positive denominator. If the denominator is zero or negative, it does not give a positive finite equilibrium area; basin limits and overflow must be considered.

### River Width and Mountain Coverage

**Purpose:** Give rivers visible width while limiting water spreading onto high banks and mountains.

River width increases logarithmically with accumulated flow. A logarithm increases quickly at first, then more slowly. This lets a large river appear wider without making its width directly proportional to its entire drainage area. The original README does not give the width constants needed for a numerical width calculation.

A nearby location can be wet only if it is within the channel's calculated width and is no more than 1.15 heightmap units above the nearest channel location:

```math
h_i-h_{\text{channel}}\leq1.15
```

With the current elevation conversion, that height difference is:

```math
1.15\left(\frac{1500}{255}\right)=6.765\ \text{m}
```

The 70th elevation percentile separates the high-terrain group, roughly the highest 30% of locations, with ties potentially affecting the exact size. At most 25% of that group can be wet. For a group of 3000 points:

```math
\text{maximum wet points}=0.25(3000)=750
```

If too many qualify, lower wet locations are kept first. These are visual placement rules rather than a complete flooding model.

### River Erosion

**Purpose:** Lower the ground where rivers cut into it.

The model makes erosion increase with both flow and slope:

```math
E_i=K_{\text{eff},i}\sqrt{Q_i}\,S_i
```

Here, $E_i$ is erosion rate in m/year, $Q_i$ is runoff-weighted contributing area in the model's area convention, and $S_i$ is downstream slope, calculated as height drop divided by horizontal distance. The coefficient $K_{\text{eff},i}$ controls how easily the ground erodes.

Doubling slope doubles the erosion rate if the other values stay fixed. Multiplying $Q$ by four doubles its square root, so it also doubles erosion.

Plants reduce the coefficient:

```math
K_{\text{eff}}=K_0(1-0.7V),\qquad K_0=2\times10^{-6}\ \text{year}^{-1}
```

The vegetation cover $V$ ranges from 0 for bare ground to 1 for full cover. At full cover, the multiplier is $1-0.7=0.3$, reducing the coefficient by 70%.

**Example:** With no plants, $Q=1000000$ m² and $S=0.1$:

```math
E=(2\times10^{-6})\sqrt{1000000}(0.1)=0.0002\ \text{m/year}
```

That is 0.2 mm/year. Full plant cover reduces it to 0.06 mm/year under the same flow and slope.

For the actual height update, the simulator works upstream from river mouths and uses the downstream point's newly updated height. This is called an **implicit update**, and it helps long steps remain stable:

```math
F_i=\frac{K_{\text{eff},i}\Delta t\sqrt{Q_i}}{\Delta d_i}
```

```math
H_{i,\text{new}}=\frac{H_i+F_iH_{\text{downstream,new}}}{1+F_i}
```

Here, $\Delta d_i$ is the distance to the receiver. The second formula is a weighted average of the current height and the updated downstream height. Larger $F$ moves the point closer to downstream elevation.

For $K_{\text{eff}}=2\times10^{-6}$ per year, $\Delta t=1000$ years, $Q=1000000$ m², and $\Delta d=100$ m, $F=0.02$. If the current height is 100 m and the updated downstream height is 90 m:

```math
H_{\text{new}}=\frac{100+0.02(90)}{1.02}=99.80392\ \text{m}
```

The point loses about 0.196 m. This update accounts for the slope changing as the point lowers, so it need not equal the initial erosion rate multiplied by the whole step duration.

### Sediment Transport and Deposition

**Purpose:** Move eroded material downstream and deposit part of it along the way.

At each location, the fraction deposited is:

```math
f=\min\left(1,\frac{0.5(\Delta x)^2}{A}\right)
```

Here, $(\Delta x)^2$ is cell area and $A$ is contributing drainage area. The minimum with 1 prevents depositing more than 100% of the available sediment. A larger drainage area gives a smaller deposited fraction, allowing large rivers to carry sediment farther.

```math
\text{deposited sediment}=f(\text{incoming sediment})
```

For 100 m grid spacing and a drainage area of 1,000,000 m²:

```math
f=\frac{0.5(100^2)}{1000000}=0.005=0.5\%
```

If 100 m³ arrives, 0.5 m³ is deposited and 99.5 m³ continues downstream. Spread over the 10,000 m² cell, that deposit raises its surface by:

```math
\text{height increase}=\frac{0.5}{10000}=0.00005\ \text{m}
```

Locally eroded material also enters the transported sediment. Lakes trap sediment until they fill, and sediment reaching the map edge is recorded as washed off.

The conservation check is:

```math
\text{remaining terrain material}+\text{exported material}
=\text{initial terrain material}+\text{uplift addition}
```

All terms must use consistent units and the same reference. Without uplift, remaining material plus exported material should stay constant.

### Plant Growth and Carrying Capacity

**Purpose:** Grow vegetation toward the amount that local conditions can support.

Vegetation cover $V$ ranges from 0 to 1. A value of 0.4 means 40% cover. The **carrying capacity** $C$ is the cover supported by temperature, rainfall, and slope.

Each condition gives a factor from 0 to 1:

```math
f_T=\mathrm{clip}_{01}\left(\frac{T_{\text{annual}}+4}{6}\right)
```

```math
f_P=\mathrm{clip}_{01}\left(\frac{P-150}{650}\right)
```

```math
f_S=\mathrm{clip}_{01}\left(\frac{55-\beta}{20}\right)
```

Here, $T_{\text{annual}}$ is local annual average temperature in °C, $P$ is annual rainfall in mm/year, and $\beta$ is slope angle in degrees. Clipping keeps each factor between 0 and 1.

The temperature factor rises from zero at −4°C to one at 2°C. The rainfall factor rises from zero at 150 mm/year to one at 800 mm/year. The slope factor is one up to 35° and falls to zero at 55°.

Multiply the factors to find carrying capacity:

```math
C=f_Tf_Pf_S
```

At −1°C, 475 mm/year, and 45°, each factor equals 0.5. Therefore, $C=0.5^3=0.125$, meaning conditions support 12.5% cover. If any factor is zero, the capacity is zero.

Growth follows a **logistic model**. When cover is low, plants can expand; as cover approaches capacity, growth slows. If existing cover exceeds capacity, it decreases toward capacity. The formula for positive starting cover and capacity is:

```math
V(t)=\frac{C}{1+\left(\frac{C-V_0}{V_0}\right)e^{-rt}}
```

Here, $V_0$ is starting cover, $r$ is growth rate per year, and $t$ is elapsed years. The exponential term controls how quickly cover approaches capacity.

The base rate is 0.15 per year. A light multiplier between 0.3 and 1.7 changes it to between $0.15(0.3)=0.045$ and $0.15(1.7)=0.255$ per year.

For $C=0.8$, $V_0=0.1$, $r=0.15$, and $t=10$:

```math
V(10)=\frac{0.8}{1+7e^{-1.5}}=0.31227
```

Cover grows from 10% to about 31.23% over ten years, before spreading or fire is applied. This calculation treats capacity and growth rate as fixed over the interval. Zero starting cover and zero capacity require separate handling because the displayed formula would involve division by zero.

### Plant Spreading and Fire

**Purpose:** Let vegetation spread into nearby ground and model the loss of cover caused by fire.

Spreading moves a location's plant cover partway toward its neighbours' average:

```math
V_{\text{new}}=V+s(\overline{V}_{\text{neighbours}}-V)
```

```math
s=\min\left(0.25,\frac{300\Delta t}{(\Delta x)^2}\right)
```

The coefficient 300 m²/year controls spreading. The cap of 0.25 means one spreading update closes at most 25% of the difference from the neighbours' average.

For 100 m spacing and a one-year step, $s=300/100^2=0.03$. If local cover is 0.1 and neighbouring average cover is 0.5:

```math
V_{\text{new}}=0.1+0.03(0.5-0.1)=0.112
```

Cover rises from 10% to 11.2%. For a ten-year step, the uncapped factor is 0.3, so the model uses 0.25. A minimum 1% seed cover is maintained where growth is possible, helping burned areas recover.

The planning model also compares spreading with a continuous growth-and-diffusion model using this approximate front speed:

```math
c\approx2\sqrt{rD_v}
```

With $r=0.15$ per year and $D_v=300$ m²/year, $c\approx2\sqrt{45}=13.42$ m/year. This is a theoretical comparison, not an exact spreading speed for the capped grid update.

The flame sensor or B key triggers a burn inside a circle with radius one tenth of the map width:

```math
R_{\text{burn}}=0.1L,\qquad V_{\text{after}}=0.5V_{\text{before}}
```

A 1000 m wide map has a 100 m burn radius. Cover of 0.8 falls to 0.4 after one burn and 0.2 after another without regrowth.

Fire also changes erosion protection. At cover 0.8, the erosion multiplier is $1-0.7(0.8)=0.44$. After the first burn it is $1-0.7(0.4)=0.72$. Holding other factors fixed, erosion becomes $0.72/0.44=1.636$ times as large, an increase of about 64%.

### Terrain Rendering

**Purpose:** Turn the height grid into a visible 3D surface.

Each grid point becomes a vertex with a horizontal position and a vertical position based on height. Display scaling stretches the mesh to its visible size.

Each square between neighbouring vertices is divided into two triangles. For a grid with $n$ points across and $m$ points down:

```math
\text{number of squares}=(n-1)(m-1)
```

```math
\text{number of triangles}=2(n-1)(m-1)
```

A 100 by 100 grid therefore has $2(99)(99)=19602$ triangles. Subtracting one is necessary because 100 points create only 99 gaps in each direction.

The renderer estimates slopes and uses them to calculate **surface normals**, directions perpendicular to the surface. Lighting uses these directions to show which slopes face the light.

Triangle connections and texture coordinates are built once. Later updates replace heights and normals while reusing those connections.

### Water Rendering and Animation

**Purpose:** Draw water and make it appear to flow.

Each wet location receives a small surface made of two triangles. These surfaces overlap slightly to reduce gaps. Their corners sample terrain heights between grid points, and a small vertical offset places the water above the ground to reduce flickering.

When terrain height changes, water surfaces move vertically to follow it. The drainage and lake-balance calculations determine placement.

Repeating mathematical waves create ripple crests and brightness changes in the blue texture. Shifting the texture over time makes the ripples appear to move. This produces a visual flow effect rather than calculating physical water velocity.

### Procedural Terrain Generation

**Purpose:** Create a heightmap from a generated pattern instead of a real-world image.

The generator combines four layers of simplex noise. Noise supplies smoothly varying values that can form hills and valleys.

Each successive layer doubles the sampling frequency and halves the amplitude. Relative to the first layer:

| Layer | Frequency multiplier | Amplitude multiplier |
| --- | --- | --- |
| 1 | 1 | 1 |
| 2 | 2 | 0.5 |
| 3 | 4 | 0.25 |
| 4 | 8 | 0.125 |

Lower-frequency layers create broad features. Higher-frequency layers add smaller details with less influence on the final height. The seed selects the pattern, while the frequency setting controls how much variation fits into the image.

The combined values are converted into grayscale values from 0 to 255 and saved as a heightmap. The current main program loads its configured heightmap; it does not automatically run the generator.

### Saved Maps and Charts

**Purpose:** Make changes and disagreements easier to inspect.

The change map uses current height minus original height. A location changing from 100 to 97 has a change of −3 and appears red for height loss. A change from 100 to 103 is +3 and appears blue for height gain. Equal-sized losses and gains use comparable colour intensity.

The history chart plots the land-changed and soil-moved percentages against simulated time, with a separate axis for recorded sea-level temperature. The uncertainty map shows where the alternative runs finish with the most different heights.

### River Network and Steady-State Checks

**Purpose:** Check whether the simulated landscape develops plausible large-scale relationships and whether uplift and erosion approach balance.

Hack's law relates river length to drainage area using a power function:

```math
L_{\text{river}}=cA^b
```

Here, $A$ is drainage area, $c$ is a scale constant, and $b$ is the scaling exponent. Taking logarithms gives a straight-line relationship:

```math
\log L_{\text{river}}=\log c+b\log A
```

This has the same form as $y=mx+k$. On a graph of log river length against log drainage area, the slope is $b$. Use the same logarithm base on both axes.

The exponent describes how rapidly river length increases with drainage area. If area becomes four times as large and $b=0.56$:

```math
\frac{L_{\text{new}}}{L_{\text{old}}}=4^{0.56}=2.173
```

Length becomes about 2.17 times as large. The exponent is measured from the resulting network rather than imposed on it. The original README reports a common real-river range of about 0.5 to 0.6 and cites planning-document results of 0.56 for the real-world map after one million simulated years. It also reports an increase from 0.37 to 0.48 for a noise map over five million years. These are reported results, not new measurements from this README update.

The steady-state check compares upward tectonic movement with downward river erosion. Using the erosion formula, balance occurs when:

```math
U=K_{\text{eff}}\sqrt{Q}\,S
```

Rearranging to find the slope needed for balance:

```math
S=\frac{U}{K_{\text{eff}}\sqrt{Q}}
```

For $U=0.0003$ m/year, $K_{\text{eff}}=2\times10^{-6}$ per year, and $Q=1000000$ m²:

```math
S=\frac{0.0003}{(2\times10^{-6})(1000)}=0.15
```

A slope of 0.15 means 15 m of elevation change per 100 m horizontally. Under these conditions, the erosion and uplift rates balance.

The original README reports an erosion-to-uplift ratio of 0.97 after forty million simulated years. Since exact balance is 1, this means erosion was 97% of uplift, leaving a 3% difference relative to the uplift rate.

---

Created using textures from ambientCG.com,
licensed under the Creative Commons CC0 1.0 Universal License.
>>>>>>> 6f462d55238ad6b8f075802de15a3d4c03da83a4
