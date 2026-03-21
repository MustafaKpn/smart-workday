#app/processor/queue.py

from sqlalchemy import text

def claim_jobs(conn):
    """
    Atomically claim jobs using FOR UPDATE SKIP LOCKED.
    Prevents multiple workers processing same job.
    """
    result = conn.execute(text("""
        UPDATE raw_jobs
        SET status = 'processing'
        WHERE id IN (
            SELECT id FROM raw_jobs
            WHERE status = 'pending' OR status='failed'
            LIMIT :limit
            FOR UPDATE SKIP LOCKED
        )
        RETURNING *
    """))

    return [dict(row._mapping) for row in result]