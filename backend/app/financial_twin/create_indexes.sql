-- Enterprise Upgrade: Indexes for Financial Twin

-- Enables fast filtering by warehouse, reducing full table scans on the inventory table.
CREATE INDEX IF NOT EXISTS idx_inventory_warehouse 
ON inventory(warehouse_id);

-- Depending on shipment table size, this might also be an essential index:
CREATE INDEX IF NOT EXISTS idx_shipments_shipment_id 
ON shipments(shipment_id);
