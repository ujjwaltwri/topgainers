-- Run this in the Supabase SQL Editor to replace client-side aggregation
-- Also run fix_rpcs.sql (get_distinct_*) and the get_market_breadth function below.

CREATE OR REPLACE FUNCTION get_sector_performance(period_param TEXT)
RETURNS TABLE (
  sector TEXT,
  stock_count BIGINT,
  avg_change DOUBLE PRECISION,
  positive BIGINT,
  negative BIGINT
) AS $$
BEGIN
  RETURN QUERY
    SELECT
      s.sector,
      COUNT(*)::BIGINT AS stock_count,
      AVG(g.pct_change) AS avg_change,
      COUNT(*) FILTER (WHERE g.pct_change > 0)::BIGINT AS positive,
      COUNT(*) FILTER (WHERE g.pct_change < 0)::BIGINT AS negative
    FROM gains g
    JOIN stocks s ON g.ticker = s.ticker
    WHERE g.period = period_param
      AND s.sector IS NOT NULL
    GROUP BY s.sector
    ORDER BY avg_change DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_country_performance(period_param TEXT)
RETURNS TABLE (
  country TEXT,
  stock_count BIGINT,
  avg_change DOUBLE PRECISION,
  positive BIGINT,
  negative BIGINT
) AS $$
BEGIN
  RETURN QUERY
    SELECT
      s.country,
      COUNT(*)::BIGINT AS stock_count,
      AVG(g.pct_change) AS avg_change,
      COUNT(*) FILTER (WHERE g.pct_change > 0)::BIGINT AS positive,
      COUNT(*) FILTER (WHERE g.pct_change < 0)::BIGINT AS negative
    FROM gains g
    JOIN stocks s ON g.ticker = s.ticker
    WHERE g.period = period_param
      AND s.country IS NOT NULL
    GROUP BY s.country
    ORDER BY avg_change DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_exchange_performance(period_param TEXT)
RETURNS TABLE (
  name TEXT,
  stock_count BIGINT,
  avg_change DOUBLE PRECISION,
  positive BIGINT,
  negative BIGINT
) AS $$
BEGIN
  RETURN QUERY
    SELECT
      s.exchange AS name,
      COUNT(*)::BIGINT AS stock_count,
      AVG(g.pct_change) AS avg_change,
      COUNT(*) FILTER (WHERE g.pct_change > 0)::BIGINT AS positive,
      COUNT(*) FILTER (WHERE g.pct_change < 0)::BIGINT AS negative
    FROM gains g
    JOIN stocks s ON g.ticker = s.ticker
    WHERE g.period = period_param
      AND s.exchange IS NOT NULL
    GROUP BY s.exchange
    ORDER BY avg_change DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_marquee_data(period_param TEXT)
RETURNS TABLE (
  name TEXT,
  stock_count BIGINT,
  pct_change DOUBLE PRECISION
) AS $$
BEGIN
  RETURN QUERY
    SELECT
      s.exchange AS name,
      COUNT(*)::BIGINT AS stock_count,
      AVG(g.pct_change) AS pct_change
    FROM gains g
    JOIN stocks s ON g.ticker = s.ticker
    WHERE g.period = period_param
      AND s.exchange IS NOT NULL
    GROUP BY s.exchange
    HAVING COUNT(*) > 5
    ORDER BY AVG(g.pct_change) DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_market_breadth(period_param TEXT)
RETURNS JSON AS $$
DECLARE
  total_count BIGINT;
  positive_count BIGINT;
  negative_count BIGINT;
BEGIN
  SELECT
    COUNT(*),
    COUNT(*) FILTER (WHERE g.pct_change > 0),
    COUNT(*) FILTER (WHERE g.pct_change < 0)
  INTO total_count, positive_count, negative_count
  FROM gains g
  WHERE g.period = period_param;

  RETURN json_build_object(
    'total', total_count,
    'positive', positive_count,
    'negative', negative_count,
    'pct_positive', CASE WHEN total_count > 0 THEN ROUND((positive_count::NUMERIC / total_count) * 100, 1) ELSE 0 END
  );
END;
$$ LANGUAGE plpgsql;

-- Called by pipeline after each run to fill vs_sector and vs_country
CREATE OR REPLACE FUNCTION compute_relative_strength()
RETURNS VOID AS $$
BEGIN
  -- Fill sector_avg_change and vs_sector
  UPDATE gains g
  SET
    sector_avg_change = sub.avg_change,
    vs_sector = g.pct_change - sub.avg_change
  FROM (
    SELECT g2.period, s2.sector, AVG(g2.pct_change) AS avg_change
    FROM gains g2
    JOIN stocks s2 ON g2.ticker = s2.ticker
    WHERE s2.sector IS NOT NULL
    GROUP BY g2.period, s2.sector
  ) sub
  JOIN stocks s ON s.ticker = g.ticker
  WHERE g.period = sub.period AND s.sector = sub.sector;

  -- Fill country_avg_change and vs_country
  UPDATE gains g
  SET
    country_avg_change = sub.avg_change,
    vs_country = g.pct_change - sub.avg_change
  FROM (
    SELECT g2.period, s2.country, AVG(g2.pct_change) AS avg_change
    FROM gains g2
    JOIN stocks s2 ON g2.ticker = s2.ticker
    WHERE s2.country IS NOT NULL
    GROUP BY g2.period, s2.country
  ) sub
  JOIN stocks s ON s.ticker = g.ticker
  WHERE g.period = sub.period AND s.country = sub.country;
END;
$$ LANGUAGE plpgsql;
