# Pillar 6 Technical Deep-Dive: Inventory & Opportunity Costs
**The Algorithmic Core of Modeling "Parked Capital"**

---

## 🏛️ I. The Objective: Illuminating the "Invisible Costs"
Most logistics tools focus on the **Freight Bill** ($10k for a ship). They ignore the fact that the **$1,000,000 cargo** on that ship is losing money every second it isn't on a shelf. **Pillar 6** exists to turn "Transit Days" into "Interest Payments." 

Pillar 6 is the **"CFO's Lens"** on the global supply chain.

---

## 🔬 II. The Algorithm: A to Z

### Step 1: Capital Rate Calibration (WACC)
We ingest the company’s **Weighted Average Cost of Capital (WACC)** or their baseline interest rate ($i$).
*   **Logic**: If the company borrows at 8%, every $1 that isn't being sold is costing them money.

### Step 2: Daily Opportunity Cost ($O_d$)
We calculate the "Interest" lost for every day the shipment stays in transit. 
*   **Formula**: $O_d = \frac{\text{Shipment Value} \times (i / 365)}{100}$.
*   **Example**: A $1M shipment at 8% WACC costs **$219 per day** just in "Lost Interest."

### Step 3: Physical Holding Cost ($H_d$)
We add the actual physical costs of storage.
1.  **Warehousing**: $2/pallet/day$.
2.  **Insurance**: A proportional daily premium.
3.  **Shrinkage/Obsolescence**: A daily "Value Decay" ($\lambda$) based on product category (e.g., iPhones lose value faster than steel).

### Step 4: Temporal Cumulative Math (The Link to Pillar 4)
As the **Temporal Cone (Pillar 4)** moves (e.g., a 5-day delay is detected), Pillar 6 adds the **Cumulative Growth** of these costs to the **EFI (Pillar 5)**.
*   **Math**: $\text{Total Hidden Cost} = \int_{0}^{T} (O_d + H_d + \lambda V) dt$.

### Step 5: Real-Time Liquidity Impact
The system communicates with the **LlmGateway (Pillar 12)** to generate a narrative:
*   *"A 7-day delay in this shipment is not just a 'Delay'; it is an additional **$3,400 in hidden interest costs** and a 2% increase in obsolescence risk."*

---

## 🏹 III. The "Investment-Ready" Hook

### The "Hidden Profitability" Argument:
"Our competitors don't know what 'WACC' means. They think logistics is about 'Trucks.' We know logistics is about **Working Capital**. We are the only platform that shows the CEO exactly how much 'Cash is Trapped' in their supply chain at any given millisecond."

### The "Surgical Inventory" Argument:
"Because we model **Physical Decay** (Pillar 6), our system can prioritize a shipment of perishable pharmaceuticals or high-fashion over a shipment of grain, even if the grain has a higher total value. We optimize for **Liquidity**, not just volume."

---
**Verdict**: Pillar 6 is the "CFO's Secret Weapon." It turns a "Logistic Problem" into a "Balance Sheet Optimization." 🚀📐💰🦾📈
