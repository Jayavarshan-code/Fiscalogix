SELECT warehouse_id, SUM(quantity) as total_items 
FROM inventory 
GROUP BY warehouse_id;