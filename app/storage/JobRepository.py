from typing import List, Dict, Optional
from sqlalchemy import text, insert
from app.storage.db import raw_jobs, parsed_jobs 


class JobRepository:
    def __init__(self, engine):
        self.engine = engine

    def bulk_insert(self, jobs: List[Dict]) -> int:
        if not jobs:
            return 0

        with self.engine.connect() as conn:
            inserted = 0
            for job in jobs:
                stmt = insert(raw_jobs).prefix_with("OR IGNORE").values(job)
                result = conn.execute(stmt)
                inserted += result.rowcount
            conn.commit()
            return inserted

    def claim_jobs(self) -> List[Dict]:
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM raw_jobs
                WHERE status IN ('pending', 'failed')
            """))
            jobs = [dict(row._mapping) for row in result]

            if not jobs:
                return []

            ids = [j["id"] for j in jobs]
            placeholders = ",".join(str(i) for i in ids)
            conn.execute(text(f"""
                UPDATE raw_jobs
                SET status = 'processing'
                WHERE id IN ({placeholders})
            """))
            conn.commit()

        return jobs

    def mark_completed(self, job_id: int, score: float, reasoning: str):
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE raw_jobs
                SET status = 'completed', processed_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """), {"id": job_id})

            conn.execute(text("""
                INSERT INTO parsed_jobs (id, score, reasoning, created_at)
                VALUES (:id, :score, :reasoning, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET
                    score = excluded.score,
                    reasoning = excluded.reasoning,
                    created_at = CURRENT_TIMESTAMP
            """), {"id": job_id, "score": score, "reasoning": reasoning})

            conn.commit()

    def mark_failed(self, job_id: int):
        with self.engine.connect() as conn:
            conn.execute(text("""
                UPDATE raw_jobs
                SET status = 'failed', processed_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """), {"id": job_id})
            conn.commit()

    def get_job_by_id(self, job_id: int) -> Optional[Dict]:
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM raw_jobs WHERE id = :id
            """), {"id": job_id})
            row = result.fetchone()
            return dict(row._mapping) if row else None