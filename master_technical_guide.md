# Fiscalogix: Master Technical Guide (Pillars 1 - 9)
**The Definitive Technical Architecture for Global Trade Intelligence**

---

## 🏛️ Pillar 1: The AIFieldMapper
### 🔬 The Algorithm: A to Z

#### Step 1: Input Sensing & Feature Extraction
We ingest the **Headers** and **Sample Data Rows**.
*   **Header**: `EXPECTED_DLV_DATE`
*   **Sample Data**: `['2025-03-24', '2025-03-26']`
*   **Math**: We generate a **Semantic Embedding Vector ($E_s$)** using a Large Language Model (e.g., Ada-002 or Llama-3-Embed).

#### Step 2: Cross-Encoder Scoring (The Match)
We compare the Source Vector ($E_s$) against every field in the **Master Schema ($E_m$)**.
*   **Formula**: $Score = \cos(\theta) = \frac{E_s \cdot E_m}{\|E_s\| \|E_m\|}$
*   **Heuristic Weight**: We add weights for exact string matches or known ERP abbreviations (e.g., `ETA` = `Expected Time of Arrival`).

#### Step 3: Bayesian Disambiguation (The Confirm)
If we find two high-scoring matches (e.g., `Departure_Date` and `Arrival_Date`), we look at the **Data Values**.
*   **Algorithm**: We check $P(\text{Field} | \text{Data Distributions})$. 
*   **Logic**: If $Date_A < Date_B$, then $Date_A$ is likely the `Departure` and $Date_B$ is the `Arrival`.

#### Step 4: Logic Projection (Pydantic Mapping)
The system then auto-generates a **Dynamic Transformation Layer**.
*   **Output**: A Pydantic model or a Python dictionary mapper that "casts" the raw ERP data into the high-precision Fiscalogix objects used by the EFI Engine (Pillar 5).

---

## 🛰️ Pillar 2: The RiskRadar (Spatial H3 Grid-State)

### 🔬 The Algorithm: A to Z

#### Step 1: Spatial Quantization (The Conversion)
We take a continuous coordinate $(Lat, Lon)$—which is a float—and project it onto the H3 honeycomb.
*   **Math**: The world is divided into 12 original icosahedron faces. H3 recursiveley subdivides these into hexagons. 
*   **Resolution**: We use **Resolution 7** (avg. area ~5 $km^2$). 
*   **Output**: A 64-bit integer `H3Index` (e.g., `872830828ffffff`).

#### Step 2: Spatial Hash Map (The Global State)
Instead of a database table, we maintain a **Global Risk Hash Map** in memory.
*   **Key**: `H3Index`
*   **Value**: `RiskScore` (0.0 to 1.0) based on AIS density, Weather severity, and Port congestion.

#### Step 3: The O(1) Spatial Join (The Performance Leap)
This is where we kill the competition. To check if a ship is in danger:
*   **Legacy**: Calculate distance to every storm on earth.
*   **Fiscalogix**: `is_in_danger = risk_map.get(Ship.H3Index) > threshold`
*   **Performance**: One CPU instruction. One memory lookup. **Constant Time $O(1)$**.

#### Step 4: k-Ring Neighbor Expansion
What if the storm is *next* to the ship?
*   **Algorithm**: We use `h3.k_ring(current_index, k=1)`. 
*   **Result**: Instantly returns the 6 surrounding Hex IDs. We check these 6 IDs against the Risk Map.

---

## 🏙️ Pillar 3: The H3 Matrix (Visualization)

### 🔬 The Algorithm: A to Z

#### Step 1: Hierarchical Bit-Shifting (The "Zoom" Math)
H3 indices are 64-bit integers. A unique property of H3 is that a **Parent Hex** contains its **Children Hexes** within its bit-structure.
*   **Math**: To "Zoom Out" from Res 9 to Res 7, we don't recalculate geometry. We simply **Shift the Bits** of the 64-bit integer.
*   **Performance**: This is the fastest operation in computer science (single CPU cycle).

#### Step 2: Recursive Risk Aggregation (The "Heatmap" Logic)
As we zoom out, we must "Summarize" the risk. 
*   **Algorithm**: We sum the `RiskScore` (Pillar 2) of all children into the parent.
*   **Normalization**: $Parent\_Risk = \min(1.0, \frac{\sum{Child\_Risk}}{7})$.

#### Step 3: WebGL Instanced Rendering (The "Display" Logic)
Rendering 10,000 individual SVG hexagons would crash a browser. 
*   **Solution**: We use **WebGL Buffer Geometry**. We send a single "Hexagon Template" to the GPU and tell it to "Instance" it at 10,000 different coordinates with different color attributes (from the Risk Map).

---

## ⏳ Pillar 4: The Temporal Risk Timeline

### 🔬 The Algorithm: A to Z

#### Step 1: Monte Carlo Integration (The Data Source)
We ingest 1,000 real-time simulations of the current shipment from the **EFI Engine (Pillar 5)**. 

#### Step 2: Temporal Binning (The Clumping)
We group these 1,000 simulations into discrete **Temporal Bins** (e.g., 30-minute intervals).
*   **Math**: A **Kernel Density Estimation (KDE)** is performed to create a continuous probability curve.
*   **Distribution Type**: We use a **Beta Distribution** ($\alpha, \beta$).

#### Step 3: Probabilistic Decay (The "Cone" Effect)
As the vessel gets closer to the port, the **Standard Deviation ($\sigma$)** of the distribution shrinks.
*   **Math**: We use a **Recursive Bayesian Update** (Kalman-style). We only apply the "Delta" of current speed vs. average speed to the existing Beta curve.

#### Step 4: Financial Penalty Weighting
We overlay the **Financial Penalties** (Stockout Costs, Demurrage) onto the Temporal Bins.
*   **Logic**: $Risk\_Value = P(t) \times Penalty(t)$.

---

## 📊 Pillar 5: Universal EFI Engine

### 🔬 The Algorithm: A to Z

#### Step 1: Variable Extraction (The "6-D" Input)
We extract six core variables: Revenue, Cost, Demurrage, Late Fines, Holding Costs, and Opportunity Costs ($R, C, D, L, H, O$).

#### Step 2: Probability Distribution (The "Link" to Pillar 4)
We receive the **Beta Distribution** (Pillar 4) of the expected arrival times. 

#### Step 3: Vectorized Monte Carlo (The "Simulation")
We run **10,000 simulations** of the shipment's arrival using **NumPy Parallel Processing**.
*   **Math**: $Cost_i = L(t_i) + H(t_i) + D(t_i) + O(t_i)$.

#### Step 4: EFI Calculation (The "Expected Value")
The EFI is the **Mean** of the 10,000 simulated costs.
*   **Formula**: $EFI = \frac{1}{N} \sum_{i=1}^{N} Cost_i$.

#### Step 5: Fidelity Penalty (The "Truth Guard")
If the **Fidelity Score** is low, we stochastically expand the **Confidence Interval**.

---

## 💰 Pillar 6: Inventory & Opportunity Costs

### 🔬 The Algorithm: A to Z

#### Step 1: Daily Opportunity Cost ($O_d$)
We calculate the "Interest" lost for every day the shipment stays in transit. 
*   **Formula**: $O_d = \frac{\text{Shipment Value} \times (i / 365)}{100}$.

#### Step 2: Physical Holding Cost ($H_d$)
We add the actual physical costs of storage, insurance, and **Valuation Decay** ($\lambda$).

#### Step 3: Temporal Cumulative Math
As the **Temporal Cone (Pillar 4)** moves, Pillar 6 adds the **Cumulative Growth** of these costs to the **EFI (Pillar 5)**.
*   **Math**: $\text{Total Hidden Cost} = \int_{0}^{T} (O_d + H_d + \lambda V) dt$.

---

## ⚖️ Pillar 7: Customs & Tax (The HS Code Engine)

### 🔬 The Algorithm: A to Z

#### Step 1: HS Classification (Fuzzy Logic)
We project product descriptions onto the universal 6-digit HS codes using hierarchical string matching.

#### Step 2: Duty Calculation
*   **Math**: $Duty = CIF\_Value \times Rate_{ODP}$.

#### Step 3: Tax Sensitivity Analysis
The engine evaluates saving via changing the "Point of Entry" (e.g., port selection).

---

## 🛡️ Pillar 8: Licenses & Permits (The Compliance Gate)

### 🔬 The Algorithm: A to Z

#### Step 1: Rule-Evaluation Engine
We use **Boolean Logic Gates** (AND/OR/NOT).
*   **Logic**: `REQUIRE {Permit} IF {Condition}`.

#### Step 2: Validity Tracking
It tracks the **Expiration Date** of the license and provides a buffer for renewal.

---

## 🛡️ Pillar 9: Document Intelligence (DIP)

### 🔬 The Algorithm: A to Z

#### Step 1: Factor 1 & 2: Multi-Model Consensus ($M_1, M_2$)
We run **GPT-4o** and **Claude 3.5** in parallel to extract key fields independently.
*   **Math**: Consensus Score ($S_c$) $1.0$ if identical, $0.0$ if different.

#### Step 2: Factor 3: Recursive Logic Verification (The "Truth Check")
We take the extracted numbers and "Run" them through the **EFI Engine (Pillar 5)**.
*   **Math**: We use **Z-Score Anomaly Detection** against historical contract norms.

---
**Final Verdict**: This Master Guide covers the **Hardened Heart** of the Fiscalogix Platform. You are ready to defend every bit and byte of this architecture. 🚀🏛️💰🌐⚖️🛡️🦾
