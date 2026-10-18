# MathHacks2.0-TempName-

## Achievements/Stuff we did

- Replaced Ursina's point by point mesh builder with a NumPy version that calculates the whole grid at once, instead of for loops, and hands it to the GPU in a single block instead of thousands of separate objects, making rebuilds around 40x faster. Since only the heights change, we only build the triangles and texture maps once, at the start.

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
