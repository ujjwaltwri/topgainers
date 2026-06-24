-- TopGainers Full Database Schema
-- Run in Supabase SQL Editor to create all tables, views, and functions from scratch.
-- For incremental updates, use drop_unused_columns.sql, fix_rpcs.sql, rpcs_aggregation.sql.

-- ── TABLES ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS stocks (
  ticker            TEXT PRIMARY KEY,
  name              TEXT,
  sector            TEXT,
  industry          TEXT,
  country           TEXT,
  region            TEXT,
  exchange          TEXT,
  currency          TEXT,
  market_cap        DOUBLE PRECISION,
  market_cap_tier   TEXT,
  pe_ratio          DOUBLE PRECISION,
  dividend_yield    DOUBLE PRECISION,
  earnings_growth   DOUBLE PRECISION,
  revenue_growth    DOUBLE PRECISION,
  ipo_date          TEXT,
  earnings_date     TEXT,
  recommendation    TEXT,
  last_updated      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gains (
  id                BIGSERIAL PRIMARY KEY,
  ticker            TEXT NOT NULL REFERENCES stocks(ticker) ON DELETE CASCADE,
  period            TEXT NOT NULL,  -- '1D','5D','1M','3M','6M','1Y','2Y','3Y','5Y','YTD','MAX'
  pct_change        DOUBLE PRECISION,
  start_price       DOUBLE PRECISION,
  end_price         DOUBLE PRECISION,
  start_date        TEXT,
  end_date          TEXT,
  avg_volume        BIGINT,
  volume_ratio      DOUBLE PRECISION,
  high_52w          DOUBLE PRECISION,
  low_52w           DOUBLE PRECISION,
  pct_from_52w_high DOUBLE PRECISION,
  pct_from_52w_low  DOUBLE PRECISION,
  at_52w_high       BOOLEAN,
  at_52w_low        BOOLEAN,
  volatility_30d    DOUBLE PRECISION,
  max_drawdown      DOUBLE PRECISION,
  rsi_14            DOUBLE PRECISION,
  ma_50             DOUBLE PRECISION,
  ma_200            DOUBLE PRECISION,
  gain_streak       INTEGER,
  sector_avg_change DOUBLE PRECISION,
  country_avg_change DOUBLE PRECISION,
  vs_sector         DOUBLE PRECISION,
  vs_country        DOUBLE PRECISION,
  UNIQUE(ticker, period)
);

CREATE TABLE IF NOT EXISTS pipeline_meta (
  key   TEXT PRIMARY KEY,
  value TEXT
);

-- ── INDEXES ───────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS gains_period_idx         ON gains(period);
CREATE INDEX IF NOT EXISTS gains_ticker_idx         ON gains(ticker);
CREATE INDEX IF NOT EXISTS gains_pct_change_idx     ON gains(pct_change DESC);
CREATE INDEX IF NOT EXISTS stocks_country_idx       ON stocks(country);
CREATE INDEX IF NOT EXISTS stocks_sector_idx        ON stocks(sector);
CREATE INDEX IF NOT EXISTS stocks_exchange_idx      ON stocks(exchange);
CREATE INDEX IF NOT EXISTS stocks_mcap_tier_idx     ON stocks(market_cap_tier);

-- ── VIEW ──────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW gains_with_stocks AS
  SELECT
    g.*,
    s.name,
    s.sector,
    s.industry,
    s.country,
    s.region,
    s.exchange,
    s.currency,
    s.market_cap,
    s.market_cap_tier,
    s.pe_ratio,
    s.dividend_yield,
    s.earnings_growth,
    s.revenue_growth,
    s.recommendation
  FROM gains g
  JOIN stocks s ON g.ticker = s.ticker;

-- ── RPCs (also in fix_rpcs.sql and rpcs_aggregation.sql) ─────────────────────

CREATE OR REPLACE FUNCTION get_distinct_countries()
RETURNS TABLE (country TEXT) AS $$
BEGIN
  RETURN QUERY SELECT DISTINCT s.country FROM stocks s WHERE s.country IS NOT NULL ORDER BY s.country;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_distinct_sectors()
RETURNS TABLE (sector TEXT) AS $$
BEGIN
  RETURN QUERY SELECT DISTINCT s.sector FROM stocks s WHERE s.sector IS NOT NULL ORDER BY s.sector;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_distinct_industries()
RETURNS TABLE (industry TEXT) AS $$
BEGIN
  RETURN QUERY SELECT DISTINCT s.industry FROM stocks s WHERE s.industry IS NOT NULL ORDER BY s.industry;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_distinct_exchanges()
RETURNS TABLE (exchange TEXT) AS $$
BEGIN
  RETURN QUERY SELECT DISTINCT s.exchange FROM stocks s WHERE s.exchange IS NOT NULL ORDER BY s.exchange;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_sector_performance(period_param TEXT)
RETURNS TABLE (sector TEXT, stock_count BIGINT, avg_change DOUBLE PRECISION, positive BIGINT, negative BIGINT) AS $$
BEGIN
  RETURN QUERY
    SELECT s.sector, COUNT(*)::BIGINT, AVG(g.pct_change),
           COUNT(*) FILTER (WHERE g.pct_change > 0)::BIGINT,
           COUNT(*) FILTER (WHERE g.pct_change < 0)::BIGINT
    FROM gains g JOIN stocks s ON g.ticker = s.ticker
    WHERE g.period = period_param AND s.sector IS NOT NULL
    GROUP BY s.sector ORDER BY AVG(g.pct_change) DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_country_performance(period_param TEXT)
RETURNS TABLE (country TEXT, stock_count BIGINT, avg_change DOUBLE PRECISION, positive BIGINT, negative BIGINT) AS $$
BEGIN
  RETURN QUERY
    SELECT s.country, COUNT(*)::BIGINT, AVG(g.pct_change),
           COUNT(*) FILTER (WHERE g.pct_change > 0)::BIGINT,
           COUNT(*) FILTER (WHERE g.pct_change < 0)::BIGINT
    FROM gains g JOIN stocks s ON g.ticker = s.ticker
    WHERE g.period = period_param AND s.country IS NOT NULL
    GROUP BY s.country ORDER BY AVG(g.pct_change) DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_exchange_performance(period_param TEXT)
RETURNS TABLE (name TEXT, stock_count BIGINT, avg_change DOUBLE PRECISION, positive BIGINT, negative BIGINT) AS $$
BEGIN
  RETURN QUERY
    SELECT s.exchange AS name, COUNT(*)::BIGINT, AVG(g.pct_change),
           COUNT(*) FILTER (WHERE g.pct_change > 0)::BIGINT,
           COUNT(*) FILTER (WHERE g.pct_change < 0)::BIGINT
    FROM gains g JOIN stocks s ON g.ticker = s.ticker
    WHERE g.period = period_param AND s.exchange IS NOT NULL
    GROUP BY s.exchange ORDER BY AVG(g.pct_change) DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_marquee_data(period_param TEXT)
RETURNS TABLE (name TEXT, stock_count BIGINT, pct_change DOUBLE PRECISION) AS $$
BEGIN
  RETURN QUERY
    SELECT s.exchange AS name, COUNT(*)::BIGINT, AVG(g.pct_change)
    FROM gains g JOIN stocks s ON g.ticker = s.ticker
    WHERE g.period = period_param AND s.exchange IS NOT NULL
    GROUP BY s.exchange HAVING COUNT(*) > 5
    ORDER BY AVG(g.pct_change) DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_market_breadth(period_param TEXT)
RETURNS JSON AS $$
DECLARE
  total_count    BIGINT;
  positive_count BIGINT;
  negative_count BIGINT;
BEGIN
  SELECT COUNT(*), COUNT(*) FILTER (WHERE g.pct_change > 0), COUNT(*) FILTER (WHERE g.pct_change < 0)
  INTO total_count, positive_count, negative_count
  FROM gains g WHERE g.period = period_param;
  RETURN json_build_object(
    'total', total_count, 'positive', positive_count, 'negative', negative_count,
    'pct_positive', CASE WHEN total_count > 0 THEN ROUND((positive_count::NUMERIC / total_count) * 100, 1) ELSE 0 END
  );
END;
$$ LANGUAGE plpgsql;

-- Called by pipeline at the end of each run
CREATE OR REPLACE FUNCTION compute_relative_strength()
RETURNS VOID AS $$
BEGIN
  UPDATE gains g
  SET sector_avg_change = sub.avg_change, vs_sector = g.pct_change - sub.avg_change
  FROM (
    SELECT g2.period, s2.sector, AVG(g2.pct_change) AS avg_change
    FROM gains g2 JOIN stocks s2 ON g2.ticker = s2.ticker
    WHERE s2.sector IS NOT NULL GROUP BY g2.period, s2.sector
  ) sub
  JOIN stocks s ON s.ticker = g.ticker
  WHERE g.period = sub.period AND s.sector = sub.sector;

  UPDATE gains g
  SET country_avg_change = sub.avg_change, vs_country = g.pct_change - sub.avg_change
  FROM (
    SELECT g2.period, s2.country, AVG(g2.pct_change) AS avg_change
    FROM gains g2 JOIN stocks s2 ON g2.ticker = s2.ticker
    WHERE s2.country IS NOT NULL GROUP BY g2.period, s2.country
  ) sub
  JOIN stocks s ON s.ticker = g.ticker
  WHERE g.period = sub.period AND s.country = sub.country;
END;
$$ LANGUAGE plpgsql;
