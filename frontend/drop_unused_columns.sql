-- Run in Supabase SQL Editor to drop gains columns never used by the frontend.
-- Verified unused by auditing: app.js, table.js, filters.js, overview.js, supabase-api.js

ALTER TABLE gains DROP COLUMN IF EXISTS sharpe_ratio;
ALTER TABLE gains DROP COLUMN IF EXISTS pct_change_usd;
ALTER TABLE gains DROP COLUMN IF EXISTS abs_change;
ALTER TABLE gains DROP COLUMN IF EXISTS recent_volume;
ALTER TABLE gains DROP COLUMN IF EXISTS above_ma_50;
ALTER TABLE gains DROP COLUMN IF EXISTS above_ma_200;

-- After dropping columns, refresh gains_with_stocks view if it exists
-- (Supabase may need this to pick up the schema change)
-- If gains_with_stocks is a VIEW, recreate it; if MATERIALIZED VIEW, refresh it.
-- Run: SELECT pg_get_viewdef('gains_with_stocks', true); to inspect it first.
