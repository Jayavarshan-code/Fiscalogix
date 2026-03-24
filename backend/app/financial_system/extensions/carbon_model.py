class CarbonTaxEngine:
    """
    Calculates Scope 3 Emissions and translates them directly into hard financial tax liabilities (e.g. EU CBAM).
    """
    def __init__(self, carbon_tax_rate_per_ton=90.0):
        # Current average European Carbon Border Adjustment Mechanism (CBAM) tax rate in USD
        self.tax_rate = carbon_tax_rate_per_ton
        
        # Approximate atmospheric distance in Kilometers
        self.route_distances = {
            "LOCAL": 500,
            "US-MX": 2500,
            "US-CN": 11600,
            "CN-EU": 8000,
            "EU-US": 7500
        }
        
        # Emissions factor: kg of CO2 emitted per ton of freight per KM
        self.carrier_emission_factors = {
            "Maersk": 0.015,         # Efficient Deep Ocean Freight
            "DHL": 0.600,            # Heavy Air Freight dependency
            "FedEx": 0.600,          # Heavy Air Freight dependency
            "LocalTransit": 0.100    # Terrestrial Trucking
        }

    def compute(self, row):
        route = row.get("route", "LOCAL")
        carrier = row.get("carrier", "LocalTransit")
        weight_tons = row.get("weight_tons", 15.0) # Assume 15 tons standard shipping container
        
        distance_km = self.route_distances.get(route, 3000)
        emission_factor = self.carrier_emission_factors.get(carrier, 0.200)
        
        # (KM) * (kg_CO2 / ton-km) * (tons) = total kg of CO2
        total_kg_co2 = distance_km * emission_factor * weight_tons
        total_tons_co2 = total_kg_co2 / 1000.0
        
        # Explicit financial penalty hitting Contribution Margin
        tax_liability = total_tons_co2 * self.tax_rate
        
        return {
            "emissions_kg": round(total_kg_co2, 2),
            "emissions_tons": round(total_tons_co2, 3),
            "tax_liability_usd": round(tax_liability, 2),
            "carrier_efficiency_rating": "Green" if emission_factor < 0.1 else "Heavy Polluter"
        }
