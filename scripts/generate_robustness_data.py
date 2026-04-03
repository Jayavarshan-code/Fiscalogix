import json
import random

def generate_robustness_data(samples=1000):
    robustness_set = []
    
    scenarios = [
        {
            "type": "false_positive_mitigation",
            "context": "Vessel is at speed 0.5 knots in H3 cell 87283. Date is January 29th (Chinese New Year). Location: Shanghai Outer Anchorage.",
            "prompt": "Is this an anomalous delay risk?",
            "response": "No. While the speed is low, the location is a known anchorage and the date corresponds with the Chinese New Year holiday. This is a planned operational wait, not a stochastic risk event."
        },
        {
            "type": "false_negative_mitigation",
            "context": "Vessel speed is 20 knots (Normal). Current H3 cell is clear. Neighboring H3 cell (87284) has an active 'Cyclonic Surge' alert for the next 4 hours.",
            "prompt": "Is the route safe?",
            "response": "Warning: Potential False Negative. While current telemetry is normal, the vessel is 15 minutes away from a high-severity cyclonic surge in the neighboring H3 cell. Strategic recommendation: Immediate course correction to the North-West."
        },
        {
            "type": "self_correction",
            "context": "Agent calculated EFI loss as $5,000 for a 2-day delay on $1M value at 8% WACC.",
            "prompt": "Audit this calculation.",
            "response": "Audit Failed. Re-calculating: ($1,000,000 * 0.08 / 365) * 2 = $438.35. The previous calculation was a hallucination. The correct EFI impact is $438.35."
        }
    ]
    
    for _ in range(samples):
        s = random.choice(scenarios)
        robustness_set.append({
            "instruction": s["prompt"],
            "input": s["context"],
            "output": s["response"],
            "meta": {"scenario_type": s["type"]}
        })
        
    return robustness_set

if __name__ == "__main__":
    data = generate_robustness_data(500) # Generating 500 samples for the demo
    with open("c:/Users/varshan/fiscalogix/scripts/robustness_training_data.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Generated 500 robustness samples in c:/Users/varshan/fiscalogix/scripts/robustness_training_data.json")
