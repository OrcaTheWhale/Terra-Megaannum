# MathHacks2.0-TempName-

Achievements/Stuff we did:
- Replaced Ursina's point by point mesh builder with a NumPy version that calculates the whole grid at once, instead of for loops, and hands it to the GPU in a single block instead of thousands of separate objects, making rebuilds around 40x faster. Since only the heights change, we only build the triangles and texture maps once, at the start.
  
  For libraries: python -m pip install -r requirements.txt

How the Simulator’s Calculations Work:

Math notation: `×` means multiplication, `^` means a power, `sqrt(...)` means square root, and `sum_i(...)` means add the expression over all grid points. `exp(x)` means e raised to x. A suffix such as `_new` labels an updated value; `h_initial_i` is the original height at point i, and `h_i(r)` is its height in alternative run r. Equations below use plain text and do not require a math renderer.

- The simulator represents terrain as a grid of height values. Each point initially has a value between 0 and 255, with bigger values showing higher ground. Calculations update the height, estimate climate and rainfall, grow vegetation, measure changes, and generate rivers and lakes.
  
Height and Elevation:
- The simulator converts heightmap values into elevations using the minimum and maximum elevations specified in the settings.
With the current range of 0 to 1500 meters, a heightmap value of 0 represents sea level, while 255 represents 1500 meters. Values between these limits are converted proportionally. This elevation conversion is used to estimate temperature at different heights. The displayed size of the terrain is controlled separately and does not determine its real elevation.

**Calculation:**

```text
H = H_min + (h / 255) × (H_max - H_min)
```

Here `h` is a heightmap value and `H` is elevation in metres. With `H_min=0` and `H_max=1500`, a value of `h=128` gives `H=128×1500/255=752.94` m. One height unit represents `1500/255=5.88235` m.

For the physical equations below, use elevation `H` in metres, horizontal grid spacing `Δx` in metres, and step duration `Δt` in years. Convert a calculated elevation change back to heightmap units using `Δh=255ΔH/(H_max-H_min)`.

Simulation Time:
- Simulation steps can represent days, seasons, years, or longer intervals. A season is treated as 91.25 days, and a year contains exactly 365 days.
The simulator tracks elapsed time by adding the duration of every completed step. It uses this total to determine the displayed year, day, and season.
The speed settings control how many simulation steps run during each frame. Increasing the speed makes simulated time pass faster on screen without changing the duration represented by an individual step.
When the user returns to an earlier step, the simulator displays a stored copy of the terrain. Continuing from that point removes the later steps and starts a new continuation.

**Calculation:**

```text
t_elapsed = sum_k(d_k)
Δt_years = d_k / 365
```

Here `d_k` is the length of step `k` in days. One day is `1/365=0.00273973` years; one season is `91.25/365=0.25` years. Two years and one season total `365+365+91.25=821.25` days, or `2.25` years.

Soil Creep:
- Soil creep gradually smooths the terrain.
For each grid point, the simulator finds the average height of its four direct neighbours. It then moves the point’s height partway toward that average. High points become lower, while depressions become higher.
The amount of change depends on the diffusion coefficient, the duration of the simulation step, and the distance between grid points. The coefficient is 0.005 square metres per year.
Long steps are divided into smaller internal updates when needed to keep the calculation stable. The stability limit depends on grid spacing and the diffusion coefficient.
At the boundaries, the simulator repeats the nearest edge height when a neighbour would fall outside the map. This prevents material from being transferred beyond the terrain.
The calculation redistributes height across the grid and should preserve the total height sum, apart from small rounding differences.

**Calculation:**

```text
∂H/∂t = D × ∇²H
D = 0.005 m²/yr
```

```text
H_i_new = H_i + α × (H_N + H_S + H_E + H_W - 4H_i)
α = D × Δt / (Δx)²
```

The four neighbour heights are `H_N,H_S,H_E,H_W`. Stability requires `4α≤1`. A sufficient number of equal substeps is `n=max(1,⌈4DΔt/Δx^2⌉)`, with each substep lasting `Δt/n`.

**Example:** For `Δx=10` m and `Δt=1000` years, `α=0.005×1000/100=0.05`. If a point is at 100 m and all four neighbours are at 90 m, its new height is `100+0.05(360-400)=98` m. The step is stable because `4α=0.2`. A 10,000-year step on the same grid needs at least `⌈2⌉=2` substeps.

Tectonic Uplift:
- Plate movement raises the terrain in a dome-shaped pattern. Uplift is fastest at the centre and falls to zero at the map edges.
The default maximum rate is 0.3 millimetres per year. Each step adds the local uplift rate multiplied by the step’s duration in years to the terrain height.

**Calculation:**

```text
U(x,y) = U_0 × sin(πx/L) × sin(πy/L)
H_new = H + U(x,y) × Δt
```

Here `x,y` are horizontal distances across a square map of width `L`, and `U_0=0.3` mm/yr `=0.0003` m/yr. At the centre, `x=y=L/2`, both sine terms equal one. Over 1000 years the centre rises `0.0003×1000=0.3` m. At an edge, one sine term is zero, so uplift is zero.

Seasonal Temperature:
- Sea-level temperature follows a smooth, repeating seasonal cycle.
The current settings use an annual average of 5°C and a seasonal variation of 15°C above or below that average. This produces temperatures ranging from approximately −10°C to 20°C before additional warming is applied.
The warmest point in the cycle is set to day 200.
For steps lasting a season or a year, the simulator calculates the average temperature across the entire interval. It does not use only the temperature at the beginning of the step. A complete year averages to the configured annual temperature plus any warming adjustment.
This is a simplified climate cycle, rather than a daily weather forecast.

**Calculation:**

```text
T_sea(t) = T_avg + 15 × cos(2π(t - 200)/365) + ΔT
```

Here `t` is elapsed time in days, `T_avg=5`°C, and `ΔT` is the combined sensor and manual warming adjustment. At day 200 with no adjustment, `T_sea=5+15=20`°C. Half a year later, the cosine is `-1`, giving `5-15=-10`°C.

For a step beginning at day `a` and lasting `d` days, averaging the continuous cycle gives:

```text
mean(T_sea) = T_avg + ΔT
            + [15/(ωd)] × [sin(ω(a + d - 200)) - sin(ω(a - 200))]
ω = 2π/365
```

For `d=365`, the sine difference is zero, giving an annual average of `5+ΔT`°C.

Temperature at Higher Elevations:
- The simulator assumes that temperature decreases by 6.5°C for every 1000 metres of elevation.
At 1500 meters, the calculated temperature is therefore 9.75°C colder than the sea-level temperature.
The simulator applies this adjustment to every point on the terrain. It then counts how many points are below 0°C and expresses that count as a percentage of the whole map.
For longer steps, this percentage uses the step’s average temperature. It does not measure how long each location remains frozen.
Temperature also determines the snow line, lake evaporation, and the temperature limit on vegetation. It does not change the soil-creep calculation.

**Calculation:**

```text
T_i = T_sea - 0.0065 × H_i
below-freezing percentage = 100 × count(points where T_i < 0) / N
```

Here `N` is the number of grid points. At `H=1500` m and `T_sea=5`°C, `T=5-0.0065×1500=-4.75`°C. If 2500 of 10,000 points are below zero, the displayed percentage is `100×2500/10000=25%`.

Snow Line and Ice:
- The snow line is the elevation where the calculated temperature reaches 0°C. It is found by dividing sea-level temperature by the temperature decrease per kilometre of elevation.
The terrain shader draws snow above this line, and lakes and rivers above it turn to ice.
If the snow line is below sea level, the whole map freezes. If it is above the highest peak, no snow is drawn.
At a sea-level temperature of 5°C, the snow line is approximately 770 metres.

**Calculation:**

```text
H_snow = T_sea / 0.0065  [metres]
```

Setting `T_i=0` in the elevation-temperature equation gives this height. At 5°C, `H_snow=5/0.0065=769.23` m. At 20°C it is 3076.92 m, above a 1500 m peak. At `-10`°C it is `-1538.46` m, so terrain at or above sea level is below freezing.

Wind-Driven Rainfall:
- Wind pushes air upward on slopes facing the wind. The rising air cools and releases moisture, giving those slopes more rain. Descending air produces drier conditions on the sheltered side, creating a rain shadow.
The calculation first smooths the terrain over 600 metres so rainfall responds to broad mountainsides.
Wind speed ranges from 2 to 20 metres per second as the wind-strength input rises from zero to one. The pendulum sensor or the Y key controls this input.
The rainfall pattern is rescaled so its average remains equal to the yearly rainfall selected in the menu. Wind redistributes rain across the map without changing that average.

**Calculation:**

```text
U = 2 + 18b
w_i = U × [cos(θ) × (∂H/∂x) + sin(θ) × (∂H/∂y)]
```

Here `b∈[0,1]` is wind strength, `θ` is wind direction, and the derivatives are slopes of the terrain after 600 m smoothing. The quantity `w_i` estimates upward air speed. For `b=0.5`, `U=11` m/s. With wind along a slope of 0.1, `w=11×0.1=1.1` m/s.

```text
P_i = mean(P) × s_i / mean(s)
mean(s) = sum_i(s_i) / N
```

Here `s_i` is the local rainfall weighting and `mean(P)` is the menu’s annual rainfall in mm/yr. For two equally sized regions with weights 1.5 and 0.5, `mean(s)=1`. An 800 mm/yr average therefore becomes 1200 mm/yr and 400 mm/yr, whose average remains 800 mm/yr. These weights illustrate the normalization; they are not fixed windward and sheltered factors. The PDF clips the end of the equation defining `s_i`, so that missing expression is not reconstructed here.

Sensor Smoothing and Calibration:
- Most sensor readings are smoothed to reduce sudden fluctuations. Each new measurement moves the stored reading 20% of the way toward the latest value. This makes the display steadier, although it also makes it respond more gradually.
The first reading is stored directly. Timestamps and wind direction are not smoothed.
Light, flame, humidity, and tilt readings are converted to a scale from zero to one using calibration endpoints. Readings outside those endpoints are limited to the nearest end of the scale.
Light and flame readings use reversed calibration because lower raw readings represent stronger detection. Humidity readings from 40 to 90 are mapped across the scale, while tilt readings from 0° to 30° determine the displayed wind strength.
The interface labels normalized humidity as “rain.” This is a demonstration input, not a measurement of rainfall. Wind strength is similarly based on tilt rather than a measured wind speed.

**Calculation:**

```text
v_smooth_new = 0.8 × v_smooth_old + 0.2 × v_raw
```

A stored temperature of 20°C followed by a raw reading of 25°C gives `0.8×20+0.2×25=21`°C. Another raw reading of 25°C gives `0.8×21+0.2×25=21.8`°C.

```text
clip_01(q) = min(1, max(0, q))
q_normal = clip_01((v - a)/(b - a))
```

For reversed calibration, use `1-q_normal`. Humidity 65 gives `(65-40)/(90-40)=0.5`. A tilt of 15° gives `15/30=0.5`. Humidity 100 gives 1.2 before clipping and 1 after clipping.

Sensor Temperature Changes:
-The first valid temperature reading becomes the starting reference.
Later readings are compared with that reference to determine how much warmer or colder the sensor has become. This difference shifts the simulator’s climate temperatures.
Manual keyboard adjustments are added to the sensor difference. Each Up or Down input changes the manual adjustment by 0.5°C.
Re-zeroing replaces the starting reference with the current smoothed temperature.
Light controls vegetation growth, wind affects the rainfall pattern, and the flame sensor can burn vegetation. These inputs can therefore affect terrain evolution indirectly through plant cover and runoff.

**Calculation:**

```text
ΔT = (T_sensor - T_reference) + 0.5 × (n_up - n_down)
```

If the reference is 20°C, the smoothed reading is 23°C, and Up has been pressed twice, `ΔT=(23-20)+0.5×2=4`°C. The annual sea-level average becomes `5+4=9`°C. Re-zeroing at 23°C resets the sensor contribution to zero while retaining any manual adjustment.

Percentage of Land Changed:
- The simulator compares each current height with its original height.
A point counts as changed when the difference is greater than one height unit. The number of changed points is divided by the total number of points and expressed as a percentage.
With the current elevation range, one height unit represents approximately 5.88 metres.
This measurement shows how much of the grid has crossed the change threshold. It does not describe the average size of those changes.

**Calculation:**

```text
Δh_i = h_i - h_initial_i
land changed (%) = 100 × count(points where |Δh_i| > 1) / N
```

If 300 of 1000 points differ from their original height by more than one unit, the result is `100×300/1000=30%`. A difference of exactly one unit is excluded.

Percentage of Soil Moved:
- The simulator adds up the height lost at points that are now lower than their original positions. It compares this total with the sum of the original terrain heights.
Height gains are excluded so the calculation does not count both a loss and its corresponding deposit.
This describes net height loss relative to the starting terrain. It does not track every movement during intermediate steps. Material could move several times without all of that movement appearing in the final percentage.
The result is a height-based indicator. It is not a direct measurement of soil mass or volume.

**Calculation:**

```text
soil moved (%) = 100 × sum_i(max(h_initial_i - h_i, 0)) / sum_i(h_initial_i)
```

For original heights `(10,20,30)` and current heights `(8,21,31)`, the losses are `(2,0,0)` and the original total is 60. The result is `100×2/60=3.33%`. Height gains are excluded from the numerator.

Total Soil and Roughness:
- The displayed total soil value is the sum of all terrain heights. Under soil creep alone, this should remain approximately constant because the calculation redistributes material within the grid. Uplift adds material, while sediment leaving the map reduces it.
Converting this value into physical soil volume or mass would require additional information, including the area represented by each grid point.
Roughness is calculated using the standard deviation of the terrain heights. It measures how spread out the elevations are around their average.
A larger value indicates greater overall elevation variation. A smaller value indicates a more level landscape. This measurement does not directly describe local steepness or small surface details.

**Calculation:**

```text
S = sum_i(h_i)
mean(h) = S / N
σ_h = sqrt(sum_i((h_i - mean(h))²) / N)
```

For heights `(10,20,30)`, `S=60`, `mean(h)=20`, and `σ_h=sqrt((100+0+100)/3)=8.165` height units. This is about `8.165×1500/255=48.03` m of elevation standard deviation under the current conversion.

Likelihood Score:
- The simulator tests how sensitive its result is to small changes in its assumptions.
It repeats the recorded simulation twenty times. Each alternative run independently adjusts starting heights by up to one height unit and varies the process rates within their configured uncertainty ranges. These include soil creep by up to 80%, river erosion by up to 70%, and uplift by up to 50% in either direction.
The alternative runs use the same recorded history as the main simulation.
The score considers points where the main terrain changed by more than two height units, approximately 12 metres with the current elevation range. It compares the amount of change in each alternative run with the main result and counts agreement within a 25% tolerance.
The displayed score averages that agreement across the twenty runs.
A high score means the result remains similar under the tested variations. It does not mean there is that probability that the real landscape will develop that way.

**Calculation:**

```text
M = points where |Δh_i| > 2
agreement_r = count(i in M where |Δh_i(r) - Δh_i| ≤ τ_i) / count(M)
likelihood (%) = (100/20) × sum over r = 1 to 20 of agreement_r
```

Here `Δh_i` is the main run’s height change, `Δh_i(r)` is the alternative run’s change, and `τ_i` is the agreement tolerance. The PDF describes agreement within 25%, but clips the full tolerance expression. Consequently, `τ_i` remains explicit rather than inventing the missing absolute-tolerance rule. The equation requires at least one point in `M`.

**Example:** If 100 points pass the change threshold and each of the twenty runs agrees at 85 of those points, `L=(100/20)×20×(85/100)=85%`.

The stated rate variations correspond to a soil-creep coefficient from `0.005(1-0.8)=0.001` to `0.005(1+0.8)=0.009` m²/yr; a river coefficient from `0.6×10^(-6)` to `3.4×10^(-6)` yr⁻¹; and maximum uplift from 0.15 to 0.45 mm/yr. These are parameter ranges for the alternative runs.

Uncertainty Map: 
- The uncertainty map measures how much the alternative simulations disagree at each location.
At every grid point, the simulator calculates the standard deviation of the alternative final heights. Higher values indicate greater disagreement, while lower values indicate more consistent results.
This uncertainty reflects the starting-height and process-rate variations included in the calculation. It does not account for every possible source of error.

**Calculation:**

```text
mean(h_i) = (1/20) × sum over r = 1 to 20 of h_i(r)
σ_i = sqrt((1/20) × sum over r = 1 to 20 of (h_i(r) - mean(h_i))²)
```

If ten runs finish at 99 units and ten at 101 units at one location, the mean is 100 and the uncertainty is `sqrt((10×1+10×1)/20)=1` height unit, about 5.88 m.

River Placement:
- The river system fills depressions to their lowest spill level before calculating drainage. It works inward from the map edges, processing the lowest unvisited point first.
This produces a surface on which enclosed hollows can drain toward an outlet. The difference between this filled surface and the ground identifies potential lake basins.
Each point checks its eight surrounding neighbours, including diagonals, and selects the lowest downhill receiver on the filled surface.
This method chooses the lowest neighbouring elevation rather than the steepest slope after accounting for diagonal distance.

**Calculation:**

```text
H_i_filled = max(H_i, min over paths p from i to edge of max over j in p of H_j)
```

For each possible route `p` from a point to the map edge, find the highest elevation along that route. The smallest of these barriers sets the spill elevation. A hollow floor at 100 m with a lowest escape barrier at 120 m has a filled elevation of 120 m and a potential water depth of `120-100=20` m. Its actual lake level also depends on the water balance.

```text
r(i) = neighbour j with the smallest H_j_filled,
       among the 8 neighbours where H_j_filled < H_i_filled
```

The receiver `r(i)` is the lowest of the eight neighbours that are lower than the point on the filled surface. This expression describes strictly downhill selection; routing across equal-height flats needs a separate tie-handling rule.

River Flow Accumulation:
- The simulator processes points from highest to lowest. Each point passes its accumulated contribution to its downhill neighbour. Lower locations therefore collect contributions from the upstream points that drain into them.
Accumulation measures the contributing drainage area. River erosion also accounts for how much rainfall becomes runoff, so wetter drainage areas supply more water.
A point becomes a river channel when its accumulated contribution reaches a threshold. This threshold is adjusted for map size so smaller maps can still produce streams.

**Calculation:**

```text
A_i = (Δx)² + sum over upstream j where r(j) = i of A_j
```

For a uniform grid, each point initially contributes its cell area. Process upstream points before their receivers. With `Δx=10` m, each cell contributes 100 m². A receiver with three upstream cells and its own cell drains `4×100=400` m². In cell-count units, that accumulation is four. Runoff-weighted accumulation additionally weights the contributions by their local runoff.

Lake Evaporation and Runoff:
- Lake evaporation is estimated at 700 millimetres per year at 8°C. It increases by approximately 7% for every additional degree of warming and decreases in colder conditions.
Not all rainfall reaches rivers. Some evaporates or is used by plants.
The simulator uses Fu’s form of the Budyko curve, with a parameter of 2.6, to divide annual rainfall between evaporation and runoff. The division depends on evaporative demand relative to rainfall.
Wet climates send a larger share of rainfall into rivers, while dry climates can lose nearly all of it to evaporation.

**Calculation:**

```text
E_lake = 700 × 1.07^(T - 8)  [mm/yr]
```

Here `T` is the temperature in °C used for the evaporation estimate. At 0°C, `E_lake=700×1.07^(-8)=407.41` mm/yr. At 25°C, it is `700×1.07^17=2211.17` mm/yr.

```text
ET/P = 1 + E/P - [1 + (E/P)^2.6]^(1/2.6)
R = P - ET
```

Here `P>0` is annual rainfall, `E` is potential evaporation, `ET` is actual evaporative loss including plant water use, and `R` is runoff, all in mm/yr. At zero rainfall the available rainfall runoff is zero, avoiding division by zero.

**Wet example:** For `P=3000` and `E=500` mm/yr, `ET=489.09` and `R=2510.91` mm/yr. **Dry example:** For `P=200` and `E=1500` mm/yr, `ET=196.94` and `R=3.06` mm/yr.

Lake Size and Overflow:
- A lake grows until incoming river water and rain on its surface balance evaporation, or until it reaches the basin’s spill level.
If the water balance supports a lake larger than the basin, it fills and overflows. Otherwise, it remains a closed lake below the spill level.
The calculation accounts for the land submerged by the lake, because that area no longer contributes land runoff.

**Calculation:**

```text
I + P × A_lake = E_lake × A_lake
```

This is the balance when `I` is the actual river inflow at the current lake size. If `I_0` instead denotes inflow before land is submerged and `R` is runoff per unit land area, use `I=I_0-RA_lake`:

```text
A_lake = I_0 / (E_lake - P + R)
```

Use inflow in m³/yr and rainfall, evaporation, and runoff in m/yr, giving lake area in m². The finite-area expression applies when its denominator is positive; compare the result with the area available below the spill level.

**Example:** With `I_0=100000` m³/yr, `E_lake=1.2` m/yr, `P=0.4` m/yr, and `R=0.2` m/yr, the equilibrium area is `100000/(1.2-0.4+0.2)=100000` m². If the basin can hold only 60000 m² below its outlet, the lake fills to the outlet and overflows.

River Width and Mountain Coverage:
- Larger accumulated flows produce wider rivers. Width grows logarithmically, so large rivers widen gradually instead of expanding in direct proportion to their upstream contributions.
The simulator finds each point’s distance from the nearest channel. Nearby points can become wet if they fall within the channel’s calculated width and are no more than 1.15 height units above the nearest channel location.
This limits water coverage on elevated banks.
The simulator also identifies high terrain using the 70th elevation percentile. It limits wet coverage within that group to 25%, keeping the lower wet locations when the limit is exceeded.
These are visual placement rules rather than a complete flooding model.

**Numerical placement rules:** A candidate location must be within its channel’s calculated width and satisfy `h_i-h_channel≤1.15` height units. Under the current elevation conversion, this height difference is `1.15×1500/255=6.765` m. If the high-terrain group contains 3000 grid points, a 25% cap allows at most `0.25×3000=750` wet points in that group. The supplied PDF does not specify the logarithmic width constants, so no numerical width equation is inferred.

River Erosion:
- Rivers cut into the terrain faster where flow is greater and the river bed is steeper.
The erosion rate follows the stream power law: it increases with the square root of runoff-weighted drainage area and directly with slope. The base erosion coefficient is 0.000002 per year.
Vegetation reduces this coefficient by up to 70% at full cover, protecting the ground beneath it.
The solver works upstream from river mouths, using each downstream neighbour’s newly calculated height. This implicit method keeps long steps, including 10,000-year steps, stable.

**Calculation:**

```text
E_i = K_eff,i × sqrt(Q_i) × S_i
K_eff,i = K_0 × (1 - 0.7 × V_i)
K_0 = 2 × 10^(-6) yr^(-1)
```

Here `Q_i` is runoff-weighted contributing area in the model’s area convention, `S_i` is downstream slope, `V_i∈[0,1]` is plant cover, and `E_i` is incision rate in m/yr. With area in m², its square root is in metres.

**Example:** Without plants, for `Q=10^6` m² and `S=0.1`, `E=2×10^(-6)×1000×0.1=0.0002` m/yr, or 0.2 mm/yr. At full cover, `K_eff=0.3K_0`, reducing the rate to 0.06 mm/yr under the same flow and slope.

The implicit height update is:

```text
F_i = K_eff,i × Δt × sqrt(Q_i) / Δd_i
H_i_new = (H_i + F_i × H_receiver_new) / (1 + F_i)
```

Here `Δd_i` is distance to the downstream receiver. If `K_eff=2×10^(-6)` yr⁻¹, `Δt=1000` years, `Q=10^6` m², and `Δd=100` m, then `F=0.02`. For `H_i=100` m and downstream updated height 90 m, `H_i^new=(100+0.02×90)/1.02=99.80392` m. This is an example of the implicit update, not a constant-rate extrapolation.

Sediment Transport and Deposition:
- Material removed by river erosion is carried downstream as sediment.
At each point, a fraction settles out. This fraction is half the grid-cell area divided by the contributing drainage area, limited to a maximum of one.
Small streams therefore deposit a larger share of their sediment locally, while larger rivers carry it farther downstream.
Lakes trap sediment until they fill, allowing deltas and deposits to build up. Sediment reaching the map edge is recorded as washed off.
Without uplift, the material remaining on the map plus the material washed off should stay constant.

**Calculation:**

```text
f_i = min(1, G × (Δx)² / A_i)
G = 0.5
D_i = f_i × Q_s,i
```

Here `A_i` is drainage area, `Q_(s,i)` is sediment arriving during the step, and `D_i` is the amount deposited, in the same units as `Q_(s,i)`. The remainder `(1-f_i)Q_(s,i)` continues downstream, with locally eroded material added to the transported sediment.

**Example:** With `Δx=100` m and `A=1000000` m², `f=0.5×10000/1000000=0.005`. From 100 m³ of incoming sediment, 0.5 m³ settles and 99.5 m³ continues. Spread over the 10000 m² cell, that deposit raises it by `0.5/10000=0.00005` m. Accounting for uplift separately, material conservation is `V_(terrain,new)+V_exported=V_(terrain,initial)+V_uplift`.

Plant Growth and Carrying Capacity:
- Vegetation cover ranges from zero for bare ground to one for full cover.
Plants grow using a logistic model, approaching the maximum cover that local conditions can support. If conditions worsen and this maximum falls below existing cover, vegetation decreases toward it.
The calculation uses the exact logistic solution so it can handle both short and long simulation steps.
The base growth rate is 0.15 per year. The light sensor scales this rate from 0.3 times the base rate in darkness to 1.7 times in bright conditions.
The maximum supported cover combines limits from annual average temperature, rainfall, and slope. Each limit ranges from zero to one, and the limits are multiplied together.
The temperature limit is zero at or below −4°C and reaches one at 2°C. The rainfall limit is zero at or below 150 millimetres per year and reaches one at 800 millimetres. The slope limit allows full cover up to 35° and falls to zero at 55°.
If any limit is zero, the location cannot support vegetation.

**Calculation:**

```text
C = clip_01((T_annual + 4)/6)
    × clip_01((P - 150)/650)
    × clip_01((55 - β)/20)
```

Here `C` is carrying capacity, `T_annual` is local annual mean temperature in °C, `P` is annual rainfall in mm/yr, and `β` is slope in degrees. At `T=-1`°C, `P=475` mm/yr, and `β=45`°, the factors are each 0.5, giving `C=0.5^3=0.125`, or 12.5% cover.

```text
dV/dt = r × V × (1 - V/C)
V(t) = C / [1 + ((C - V_0)/V_0) × exp(-r × t)]
```

Here `V_0` is the starting cover and `r=0.15m_light` yr⁻¹. The light multiplier ranges from 0.3 to 1.7, so `r` ranges from 0.045 to 0.255 yr⁻¹. The displayed exact solution assumes positive `C` and `V_0`; zero-capacity and seed-establishment cases need separate handling.

**Example:** For `C=0.8`, `V_0=0.1`, `r=0.15` yr⁻¹, and `t=10` years, `V=0.8/(1+7e^(-1.5))=0.31227`, or 31.23% cover before spreading and any fire.

Plant Spreading and Fire:
- Plants spread into nearby ground using diffusion toward neighbouring vegetation cover, with a spreading coefficient of 300 square metres per year.
Each spreading update moves cover no more than 25% of the way toward the neighbouring average. A minimum 1% seed cover is maintained where growth is possible, allowing burned areas to recover from within as well as from their edges.
The flame sensor or B key halves plant cover within a circle whose radius is one tenth of the map width each time a burn occurs.
Reduced plant cover weakens protection against river erosion until vegetation grows back.

**Calculation:**

```text
V_i_new = V_i + s × (mean(V_neighbours) - V_i)
s = min(0.25, 300 × Δt / (Δx)²)
```

For `Δx=100` m and `Δt=1` year, `s=0.03`. If a point has `V_i=0.1` and neighbouring mean cover 0.5, spreading gives `V_i^new=0.1+0.03(0.5-0.1)=0.112`. For a ten-year step, the uncapped value is 0.3 and the applied value is 0.25.

The planning document compares growth and spreading to the Fisher–KPP model, whose continuous spreading-front estimate is `c≈2sqrt(rD_v)`. At `r=0.15` yr⁻¹ and `D_v=300` m²/yr, `c≈2sqrt(45)=13.42` m/yr. This is a continuous-model comparison, not an exact speed guarantee for the capped neighbour update.

```text
V_after_burn = 0.5 × V_before_burn
R_burn = 0.1 × L
```

A 1000 m wide map has a burn radius of 100 m. Cover of 0.8 becomes 0.4 after one burn and 0.2 after a second burn without regrowth. At cover 0.8 the erosion multiplier is `1-0.7×0.8=0.44`; after the first burn it is `1-0.7×0.4=0.72`. With other factors fixed, erosion increases by `0.72/0.44=1.636`, approximately 64%.

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

```text
L_river = c × A^b
log(L_river) = log(c) + b × log(A)
```

The fitted slope `b` is Hack’s exponent. The PDF uses the symbol `h` for this exponent; `b` is used here to distinguish it from heightmap values. If drainage area increases fourfold and `b=0.56`, length increases by `4^(0.56)=2.173`, about 2.17 times.

At steady state, uplift rate and incision rate balance:

```text
U = K_eff × sqrt(Q) × S
S = U / (K_eff × sqrt(Q))
```

For `U=0.0003` m/yr, `K_eff=2×10^(-6)` yr⁻¹, and `Q=10^6` m², the equilibrium slope is `0.0003/0.002=0.15`. An erosion-to-uplift ratio of 0.97 represents a `100(1-0.97)=3%` shortfall relative to exact balance.


Created using textures from ambientCG.com,
licensed under the Creative Commons CC0 1.0 Universal License.
