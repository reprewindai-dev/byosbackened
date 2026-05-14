"""Backfill existing VeklomRun proof records into Upstash Search.

Usage:
    python scripts/backfill_upstash_search.py --limit 500

Required environment:
    UPSTASH_SEARCH_REST_URL
    UPSTASH_SEARCH_REST_TOKEN

Optional environment:
    UPSTASH_SEARCH_INDEX=default
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import desc

from core.services.upstash_search_index import configured, index_name, index_veklom_run
from db.models import VeklomRun, WorkspaceRequestLog
from db.session import SessionLocal


def backfill(limit: int, dry_run: bool) -> int:
    if not configured():
        print(
            "[upstash-search] skipped: UPSTASH_SEARCH_REST_URL and "
            "UPSTASH_SEARCH_REST_TOKEN must be configured",
            file=sys.stderr,
        )
        return 2

    indexed = 0
    skipped = 0
    db = SessionLocal()
    try:
        runs = db.query(VeklomRun).order_by(desc(VeklomRun.created_at)).limit(limit).all()
        for run in runs:
            row = None
            if run.request_log_id:
                row = db.query(WorkspaceRequestLog).filter(WorkspaceRequestLog.id == run.request_log_id).first()
            if row is None:
                skipped += 1
                continue
            if dry_run:
                indexed += 1
                continue
            ok = index_veklom_run(
                run=run,
                row=row,
                input_hash=run.input_hash,
                output_hash=run.output_hash,
                genome_hash=run.genome_hash,
            )
            indexed += 1 if ok else 0
            skipped += 0 if ok else 1
    finally:
        db.close()

    action = "would index" if dry_run else "indexed"
    print(f"[upstash-search] {action}={indexed} skipped={skipped} index={index_name()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill VeklomRun proof documents into Upstash Search.")
    parser.add_argument("--limit", type=int, default=500, help="Maximum VeklomRun rows to backfill.")
    parser.add_argument("--dry-run", action="store_true", help="Count eligible rows without writing to Upstash.")
    args = parser.parse_args()
    return backfill(limit=max(1, args.limit), dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
