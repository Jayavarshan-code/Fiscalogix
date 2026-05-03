from fpdf import FPDF
import os

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=11)

pdf.set_font("Arial", "B", size=14)
pdf.cell(200, 10, txt="MASTER SERVICE AGREEMENT - LOGISTICS AND FREIGHT", ln=True, align='C')
pdf.set_font("Arial", size=11)
pdf.ln(5)

text = """This Agreement is entered into by and between Acme Exports Ltd. ("Client") and Global Ocean Bridges ("Carrier/Supplier").

1. SCOPE OF SERVICES
The Carrier agrees to provide international ocean freight and inland drayage services for the Client.

2. SERVICE LEVEL EXPECTATIONS (OTIF)
The Carrier must maintain an On-Time In-Full (OTIF) delivery rate of no less than 95%. Delivery timestamps are calculated upon gate-in at the destination container freight station. 

3. LIQUIDATED DAMAGES AND PENALTIES
Failure to meet the agreed transit schedules will trigger the following commercial penalty structure:
a) Delay Penalties: In the event of a delay exceeding the 48-hour grace period, the Carrier shall be liable for a penalty calculated at 2.5% per day of the gross freight value.
b) Alternatively, if daily freight value calculations cannot be ascertained, a flat fee of $1,500 per day shall apply for every day beyond the expected arrival date.
c) Maximum Liability Cap: The total financial penalties levied against the Carrier for any single voyage shall not exceed 35% of the total freight invoice.

4. PAYMENT TERMS
Client shall remit payment to the Carrier within 60 days (Net 60) of invoice generation.

5. FORCE MAJEURE
Neither party shall be held liable for delays or failure in performance arising out of acts of God, extreme weather events, port strikes, or sudden governmental embargoes. In such declared Force Majeure events, standard penalty clauses described in Section 3 shall be unconditionally waived.

6. CANCELLATION AND REJECTION
If the cargo arrives more than 14 days late, the Client reserves the absolute right to reject the shipment entirely, treating the voyage as a total default.

(End of Contract)"""

for line in text.strip().split('\n'):
    pdf.multi_cell(0, 7, line)

target_path = os.path.join(os.getcwd(), "frontend", "public", "Complex_Logistics_SLA.pdf")
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "Complex_Logistics_SLA.pdf")

pdf.output(target_path)
pdf.output(desktop_path)

print(f"Generated successfully to:\\n- {target_path}\\n- {desktop_path}")
