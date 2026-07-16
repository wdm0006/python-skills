# Background Work

**Default to the simplest option that fits, and reach for Celery/RQ only when you
have genuinely outgrown all three below.** A full task-queue stack (broker + result
backend + worker fleet + monitoring) is real operational weight; most small apps
never need it.

## Option 1 — Inline in the request

Just `await` the work in the handler. No infrastructure, trivially correct, easy to
test. Use it whenever the work fits inside a reasonable request timeout.

```python
@router.post("/scan")
async def create_scan(payload: ScanIn, db: SessionDep, user: UserDep):
    result = await run_and_store_scan(db, user, payload)   # synchronous to the request
    return result
```

When it stops fitting (work takes too long, or you need it on a schedule), move to
option 2 — not straight to Celery.

## Option 2 — Cron-as-worker (the default for async/periodic work)

Run a plain `run_once()` coroutine on a schedule as a **separate process from the
same Docker image** (a platform cron job). No broker, no queue library — the
database *is* the queue. This covers polling, digests, retries, cleanup, and
draining a "send these" table.

```python
# worker.py
async def run_once() -> None:
    async with sessionmaker() as db:
        items = await claim_pending(db, limit=BATCH)   # SELECT ... FOR UPDATE SKIP LOCKED
        for item in items:
            try:
                await process(db, item)
            except Exception:
                await mark_failed(db, item)             # one bad item never stalls the batch
        await db.commit()

def main():
    import asyncio
    asyncio.run(run_once())
```

Schedule it (every 5 min, hourly, daily — whatever the work needs). Keep batches
bounded, make each item independently retryable, and add a heartbeat row so you can
alert if the worker stops running. Self-throttle with a small `app_state` table
holding budget/cooldown if the work calls rate-limited external APIs.

## Option 3 — Redis-backed job queue (interactive long-running work)

When a *user* kicks off work that's too slow for a request but they want to watch it
finish, enqueue a job, return a `job_id` immediately, and let the client poll. Back
it with Redis (`redis[hiredis]`, `redis.asyncio`) and drain it with a dedicated
worker service (again, same image, different command).

```python
@router.post("/jobs")
async def enqueue(payload: JobIn, user: UserDep) -> dict:
    job_id = await queue.enqueue(kind="report", args=payload.model_dump(), user_id=user.id)
    return {"job_id": job_id, "status": "pending"}      # client polls /jobs/{id}

@router.get("/jobs/{job_id}")
async def job_status(job_id: str, user: UserDep) -> dict:
    return await queue.get(job_id)                       # pending|processing|completed|failed
```

A `JobStatus` enum (`pending/processing/completed/failed`) and storing the result
(or error) on completion is enough — you don't need Celery's full feature set for
long-poll jobs.

### Reserve quotas, then compensate failures

If submitting a job consumes a scarce quota, reserve it atomically **before**
enqueueing; checking and incrementing separately lets concurrent requests exceed
the limit. But a reservation is not earned usage yet. Refund it if enqueue fails
or if the worker exhausts retries and dead-letters the job.

```python
period_end = await reserve_quota(       # one conditional UPDATE ... WHERE used < limit
    db, user_id=user.id
)
job = {"user_id": user.id, "reserved_period_end": period_end.isoformat()}
try:
    await queue.enqueue(job)
except Exception:
    await refund_quota(db, **job)        # compensating transaction
    raise

# Worker: refund once, only when the final retry becomes a dead letter.
if not await retry_or_dead_letter(job, error):
    await refund_quota(db, **job)
```

Make the refund conditional and idempotent (`used > 0`), and include the billing
period identity captured by the reservation. Refund only if that period is still
current; a late failure after rollover must not decrement the new period's usage.
Keep the identity needed to refund in the durable job payload, not only in an
ephemeral status record. If that record expires before the worker reads it, move
the job to a dead-letter queue and alert — do not acknowledge it as success, and
do not guess which account to refund.

## Choosing

| Situation                                            | Use            |
|------------------------------------------------------|----------------|
| Fits in a request timeout                            | Inline         |
| Periodic, or fire-and-forget, or queue-drain         | Cron-as-worker |
| User-triggered, slow, they watch it finish           | Redis job queue |
| Fan-out across many workers, chains, retries-with-backoff at scale | Celery/RQ |

Whatever you pick, the worker is **the same Docker image as the web service**, run
with a different command — never a second codebase to keep in sync.
