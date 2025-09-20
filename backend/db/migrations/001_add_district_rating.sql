-- Migration: Add district and rating columns
-- Date: 2025-01-15
-- Description: Add district column to bus_stops and rating column to convenience_stores

-- Add district column to bus_stops
ALTER TABLE bus_stops ADD COLUMN IF NOT EXISTS district TEXT;

-- Add rating column to convenience_stores  
ALTER TABLE convenience_stores ADD COLUMN IF NOT EXISTS rating DECIMAL(3,2);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_bus_stops_district ON bus_stops(district);
CREATE INDEX IF NOT EXISTS idx_convenience_stores_rating ON convenience_stores(rating);

-- Update existing data (optional)
UPDATE bus_stops SET district = '강남구' WHERE address LIKE '%강남구%';
UPDATE convenience_stores SET rating = 4.5 WHERE brand = 'GS25';
