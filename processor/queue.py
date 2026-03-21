#app/processor/queue.py

from sqlalchemy import text

def claim_jobs(conn):
    """
    Get ALL jobs that need processing and mark them as 'processing'.
    Uses locking to prevent other workers from grabbing the same jobs.
    """
    result = conn.execute(text("""
        UPDATE raw_jobs
        SET status = 'processing'
        WHERE status IN ('pending', 'failed')
        RETURNING *
    """))
    
    jobs = [dict(row._mapping) for row in result]
    return jobs