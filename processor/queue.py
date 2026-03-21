#app/processor/queue.py

from sqlalchemy import text

def claim_jobs(conn, limit=10):
    """
    Atomically claim jobs using FOR UPDATE SKIP LOCKED.
    Prevents multiple workers processing same job.
    """
    result = conn.execute(text("""
        UPDATE raw_jobs
        SET status = 'processing'
        WHERE id IN (
            SELECT id FROM raw_jobs
            WHERE status = 'pending'
            LIMIT :limit
            FOR UPDATE SKIP LOCKED
        )
        RETURNING *
    """), {"limit": limit})

    return [dict(row._mapping) for row in result]