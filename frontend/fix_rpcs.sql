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
