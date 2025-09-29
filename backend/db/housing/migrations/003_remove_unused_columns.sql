-- Remove unused columns from notices table
-- These columns were not in the normalized data and should be removed

DO $$
BEGIN
    -- Remove tenure column if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'housing' 
        AND table_name = 'notices' 
        AND column_name = 'tenure'
    ) THEN
        ALTER TABLE housing.notices DROP COLUMN tenure;
        RAISE NOTICE 'Removed tenure column from notices table';
    END IF;

    -- Remove any other unused columns that might exist
    -- Add more DROP COLUMN statements here if needed
    
END $$;
