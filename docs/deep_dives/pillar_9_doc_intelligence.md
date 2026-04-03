# Pillar 9 Technical Deep-Dive: Document Intelligence (DIP)
**The Algorithmic Core of "Legal-Grade" Autonomous Extraction**

---

## 🏛️ I. The Objective: Eliminating the "Hallucination Risk"
Most AI document tools suffer from **Hallucinations**. In a $10M logistics contract, a misplaced decimal point in a penalty clause is a fatal liability. **Pillar 9** exists to provide **"Tri-Factor Verification"**—reconciling the document to the math.

The DIP Pipeline is the **"Judge"** of the Fiscalogix system.

---

## 🔬 II. The Algorithm: A to Z

### Step 1: Multimodal OCR & Layout Sensing
We ingest the PDF/Image and use **Spatial Layout Analysis** to preserve the structure.
*   **New Native Document Support**:
    1.  **SLA Contracts**: Extracting `Free_Time_at_Port`, `Demurrage_Rates`, and `Penalty_Clauses`.
    2.  **Port Fee Schedules**: Extracting `Standard_THC`, `Security_Surcharges`, and `Congestion_Fees`.
    3.  **Customs Challans (India Focus)**: Extracting `Duty_Type`, `HS_Code`, and `IGST_Cess`.
    4.  **Licenses**: Extracting `Expiry_Date`, `Authorized_Products`, and `Geographic_Scope`.
*   **Technology**: We use a combination of Vision-LLMs (GPT-4o) and traditional OCR coordinate maps.

### Step 2: Factor 1 & 2: Multi-Model Consensus ($M_1, M_2$)
We run two independent, world-class LLMs (**GPT-4o** and **Claude 3.5**) in parallel extraction mode.
*   **The Logic**: They do not see each other’s work. They both extract the `Penalty_Value`, `Grace_Period`, and `OTIF_Threshold`.
*   **The Math**: We calculate a **Consensus Score ($S_c$)**. If $M_1 == M_2$, $S_c = 1.0$. If they differ, $S_c = 0.0$ and the field is flagged for "Human Arbitration."

### Step 3: Factor 3: Recursive Logic Verification (The "Truth Check")
This is the smartest part. We take the extracted numbers and "Run" them through the **EFI Engine (Pillar 5)**.
*   **Algorithm**: The system checks for **"Plausibility"**.
*   **Example**: If the extracted penalty is $1.0M for a $100k shipment, the AI reasons: *"Wait, this penalty is 10x the shipment value. This is statistically implausible. Re-verifying document..."*
*   **The Math**: We use **Z-Score Anomaly Detection** against historical contract norms to catch "Invisible" OCR errors.

### Step 4: The Immutable Ledger Sync (The "Evidence")
Once the document is "Tri-Factor Verified," we hash the result and save it to the **Ledger**.
*   **Outcome**: You now have a cryptographically-linked audit trail proving *exactly* what the AI read and *why* it decided it was correct.

---

## 🏹 III. The "Investment-Ready" Hook
"Our competitors use 'Predictive' AI. We use **'Deterministic' Verification**. We are the only platform that cross-checks the LLM's 'Reading' against the EFI Engine's 'Math.' This is why we can offer **Legal-Grade Reliability** that a generic OCR simply cannot."

---
**Verdict**: Pillar 9 is the "Gateway to Action." It turns a "Stack of Paper" into a "Stream of Financial Truth." 🚀📐⚖️🛡️🦾🏙️
