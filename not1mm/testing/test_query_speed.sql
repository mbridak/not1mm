-- SQLite
select count(DISTINCT(14 || ':' || 'BOTH')) as mult from dxlog where ContestNR = 3;


EXPLAIN QUERY PLAN
SELECT * FROM dxlog WHERE Mode = 'CW' ;

select count(*) as isdupe from dxlog where Call = 'ES2MC' and Mode = 'CW' and Band = '14' and 
ContestNR = 3 AND TS >= '2025-04-15 17:00:00' AND TS <= '2025-04-15 18:00:00';

EXPLAIN QUERY PLAN
select count(*) as isdupe from dxlog where Call = 'ES2MC' and Mode = 'CW' and Band = '14' and 
ContestNR = 3 AND TS >= '2025-04-15 17:00:00' AND TS <= '2025-04-15 18:00:00';