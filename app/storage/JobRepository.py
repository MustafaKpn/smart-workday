#app/storage/JobRepository.py

from typing import List, Dict, Optional
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert


class JobRepository:
    def __init__(self, engine):
        self.engine = engine


    def bulk_insert(self, jobs: List[Dict]) -> int:

        if not jobs:
            return 0
        
        from app.storage.db import raw_jobs

        stmt = insert(raw_jobs).values(jobs).on_conflict_do_nothing(index_elements=['id'])
        
        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            inserted = result.rowcount
            return inserted
        
    def claim_jobs(self, conn):
        """
        Get ALL jobs that need processing and mark them as 'processing'.
        Uses locking to prevent other workers from grabbing the same jobs.
        """
        query = text("""
            UPDATE raw_jobs
            SET status = 'processing'
            WHERE status IN ('pending', 'failed')
            RETURNING *
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query)
            jobs = [dict(row._mapping) for row in result]
            conn.commit()

        return jobs
    
    def mark_completed(self, job_id: int, score: float, reasoning: str, extracted: Dict = None):
        """Mark job as completed and save results to parsed_jobs"""
        
        with self.engine.connect() as conn:
            # Update status in raw_jobs
            conn.execute(text("""
                UPDATE raw_jobs
                SET status = 'completed', processed_at = NOW()
                WHERE id = :id
            """), {"id": job_id})
            
            # Insert results into parsed_jobs
            conn.execute(text("""
                INSERT INTO parsed_jobs (id, score, reasoning, created_at)
                VALUES (:id, :score, :reasoning, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    score = EXCLUDED.score,
                    reasoning = EXCLUDED.reasoning,
                    created_at = NOW()
            """), {
                "id": job_id,
                "score": score,
                "reasoning": reasoning
            })
            
            conn.commit()


    def get_job_by_id(self, job_id: int) -> Optional[Dict]:
        """Get a single job by ID"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM raw_jobs WHERE id = :id
            """), {"id": job_id})
            row = result.fetchone()
            return dict(row._mapping) if row else None