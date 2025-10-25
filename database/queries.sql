-- Sample queries for testing and development

-- 1. Get recent analyses for a user
SELECT 
    id,
    user_id,
    detected_salary,
    confidence,
    transactions_analyzed,
    matches_expected,
    difference,
    pdf_filename,
    pages_processed,
    created_at
FROM analyses
WHERE user_id = 'user001'
ORDER BY created_at DESC
LIMIT 10;

-- 2. Get salary analysis with metadata
SELECT 
    id,
    user_id,
    detected_salary,
    confidence,
    employer,
    pvd_rate,
    metadata->>'top_candidates' as top_candidates,
    metadata->>'clusters' as clusters,
    created_at
FROM analyses
WHERE user_id = 'user001'
ORDER BY created_at DESC;

-- 3. Get audit logs for a user
SELECT 
    action,
    status,
    processing_time_ms,
    error_message,
    created_at
FROM audit_logs
WHERE user_id = 'user001'
ORDER BY created_at DESC
LIMIT 50;

-- 4. Performance monitoring - average processing time
SELECT 
    user_id,
    action,
    AVG(processing_time_ms) as avg_time_ms,
    MAX(processing_time_ms) as max_time_ms,
    MIN(processing_time_ms) as min_time_ms,
    COUNT(*) as request_count
FROM audit_logs
WHERE status = 'success'
  AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY user_id, action
ORDER BY avg_time_ms DESC;

-- 5. Error rate by action
SELECT 
    action,
    COUNT(*) FILTER (WHERE status = 'success') as success_count,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'failed') / COUNT(*), 2) as error_rate_pct
FROM audit_logs
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY action
ORDER BY error_rate_pct DESC;

-- 6. Salary detection accuracy
SELECT 
    CASE 
        WHEN matches_expected = TRUE THEN 'Matched'
        WHEN matches_expected = FALSE THEN 'Not Matched'
        ELSE 'No Expected Value'
    END as match_status,
    confidence,
    COUNT(*) as count,
    AVG(ABS(difference)) as avg_difference,
    AVG(detected_salary) as avg_salary
FROM analyses
WHERE expected_gross IS NOT NULL
GROUP BY match_status, confidence
ORDER BY match_status, confidence;

-- 7. Daily activity summary
SELECT 
    DATE(created_at) as date,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(*) as total_analyses,
    AVG(transactions_analyzed) as avg_transactions,
    AVG(pages_processed) as avg_pages
FROM analyses
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- 8. Confidence distribution
SELECT 
    confidence,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM analyses
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY confidence
ORDER BY confidence;

-- 9. Top employers by frequency
SELECT 
    employer,
    COUNT(*) as analysis_count,
    AVG(detected_salary) as avg_salary,
    AVG(pvd_rate) as avg_pvd_rate
FROM analyses
WHERE employer IS NOT NULL
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY employer
ORDER BY analysis_count DESC
LIMIT 20;

-- 10. User activity patterns
SELECT 
    user_id,
    COUNT(*) as analysis_count,
    MIN(created_at) as first_analysis,
    MAX(created_at) as last_analysis,
    AVG(detected_salary) as avg_salary
FROM analyses
GROUP BY user_id
ORDER BY analysis_count DESC
LIMIT 50;
