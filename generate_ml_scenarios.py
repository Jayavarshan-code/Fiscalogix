import pandas as pd
import numpy as np

def generate_ml_scenarios_excel():
    # 1. False Positives (AI predicted delay, but arrived on time)
    # Impact: Wasted buffer cost, unnecessary re-routing cost
    fp_data = [
        {"Shipment ID": "SHP-FP-001", "Carrier": "Maersk", "Route": "CN-SHG to US-LGB", "Actual Delay (Days)": 0, "AI Predicted Delay (Days)": 7, "Action Taken": "Expedited Trucking", "Financial Impact (Waste)": "-$4,500", "Scenario Type": "False Positive"},
        {"Shipment ID": "SHP-FP-002", "Carrier": "MSC", "Route": "IN-BOM to EU-RTM", "Actual Delay (Days)": 1, "AI Predicted Delay (Days)": 10, "Action Taken": "Increased Safety Stock", "Financial Impact (Waste)": "-$2,100", "Scenario Type": "False Positive"},
        {"Shipment ID": "SHP-FP-003", "Carrier": "Hapag-Lloyd", "Route": "SG-SIN to US-EWR", "Actual Delay (Days)": 0, "AI Predicted Delay (Days)": 5, "Action Taken": "Air Freight Upgraded", "Financial Impact (Waste)": "-$12,000", "Scenario Type": "False Positive"}
    ]

    # 2. False Negatives (AI predicted on time, but it was delayed)
    # Impact: SLA Penalties, Stockouts, Unhappy Customers
    fn_data = [
        {"Shipment ID": "SHP-FN-001", "Carrier": "CMA CGM", "Route": "CN-YTN to US-LAX", "Actual Delay (Days)": 14, "AI Predicted Delay (Days)": 0, "Action Taken": "None (Trusted AI)", "Financial Impact (Loss)": "-$45,000 SLA Penalty", "Scenario Type": "False Negative"},
        {"Shipment ID": "SHP-FN-002", "Carrier": "Evergreen", "Route": "VN-SGN to EU-HAM", "Actual Delay (Days)": 8, "AI Predicted Delay (Days)": 1, "Action Taken": "None (Trusted AI)", "Financial Impact (Loss)": "-$18,000 Stockout", "Scenario Type": "False Negative"},
        {"Shipment ID": "SHP-FN-003", "Carrier": "ONE", "Route": "MY-PKG to US-SAV", "Actual Delay (Days)": 21, "AI Predicted Delay (Days)": 2, "Action Taken": "None (Trusted AI)", "Financial Impact (Loss)": "-$85,000 Client Churn", "Scenario Type": "False Negative"}
    ]

    # 3. True Positives (AI predicted delay, and it WAS delayed)
    # Impact: Saved Capital, Avoided SLA penalties
    tp_data = [
        {"Shipment ID": "SHP-TP-001", "Carrier": "ZIM", "Route": "CN-NGB to US-SEA", "Actual Delay (Days)": 12, "AI Predicted Delay (Days)": 10, "Action Taken": "Rerouted via Rail", "Financial Impact (Saved)": "+$30,000 Avoided Penalty", "Scenario Type": "True Positive (Value Created)"},
        {"Shipment ID": "SHP-TP-002", "Carrier": "Maersk", "Route": "TW-KHH to EU-FXT", "Actual Delay (Days)": 9, "AI Predicted Delay (Days)": 8, "Action Taken": "Client Warned Early", "Financial Impact (Saved)": "+$15,000 Client Retained", "Scenario Type": "True Positive (Value Created)"}
    ]

    df = pd.DataFrame(fp_data + fn_data + tp_data)

    writer = pd.ExcelWriter("ML_False_Positives_Negatives.xlsx", engine="xlsxwriter")
    df.to_excel(writer, sheet_name="ML Scenarios", index=False)

    # Auto-adjust column widths
    workbook = writer.book
    worksheet = writer.sheets["ML Scenarios"]
    for i, col in enumerate(df.columns):
        column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
        worksheet.set_column(i, i, column_len)

    writer.close()
    print("Excel file generated: ML_False_Positives_Negatives.xlsx")

if __name__ == "__main__":
    generate_ml_scenarios_excel()
