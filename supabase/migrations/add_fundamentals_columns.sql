-- Run this in the Supabase SQL editor (xpmfwpqkykiqmswumoxu.supabase.co)
-- Adds fundamentals columns to the stocks table

ALTER TABLE stocks ADD COLUMN IF NOT EXISTS trailing_eps       DOUBLE PRECISION;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS debt_to_equity     DOUBLE PRECISION;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS free_cashflow      DOUBLE PRECISION;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS profit_margin      DOUBLE PRECISION;
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS return_on_equity   DOUBLE PRECISION;

-- earnings_date may already exist as NULL; ensure it can store Unix timestamp or ISO string
ALTER TABLE stocks ADD COLUMN IF NOT EXISTS earnings_date      TEXT;

-- Optional cleanup: remove impossible pct_change values from prior OTC currency bug
DELETE FROM gains WHERE pct_change < -100;
