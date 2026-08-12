"""Bounded parallel execution for independent vacancy sources."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import replace
import threading
from time import monotonic
from typing import Callable, TypeVar

from app.core.deduplication import deduplicate_jobs
from app.core.models import JobPosting
from app.sources.base import (
    JobSource,
    SearchQuery,
    SourceBatch,
    SourceDiagnostic,
)


class SearchOrchestrator:
    def __init__(
        self,
        *,
        max_concurrency: int = 6,
        source_timeout_seconds: float = 45.0,
    ) -> None:
        self.max_concurrency = max(1, max_concurrency)
        self.source_timeout_seconds = max(1.0, source_timeout_seconds)

    async def search(
        self,
        sources: Iterable[JobSource],
        query: SearchQuery,
        on_progress: Callable[[SourceDiagnostic, int, int, int], None] | None = None,
    ) -> SourceBatch:
        selected = tuple(sources)
        semaphore = asyncio.Semaphore(self.max_concurrency)
        completed_count = 0
        collected_count = 0

        async def run(source: JobSource) -> tuple[list[JobPosting], SourceDiagnostic]:
            started = monotonic()
            try:
                async with semaphore:
                    source_query = replace(
                        query,
                        deadline_monotonic=(
                            monotonic() + self.source_timeout_seconds
                        ),
                    )
                    jobs = await asyncio.wait_for(
                        _call_in_daemon_thread(source.search, source_query),
                        timeout=self.source_timeout_seconds,
                    )
                partial_error = str(getattr(source, "last_partial_error", "") or "")
                return jobs, SourceDiagnostic(
                    source=source.name,
                    job_count=len(jobs),
                    elapsed_seconds=monotonic() - started,
                    error=partial_error,
                    partial=bool(partial_error),
                )
            except TimeoutError:
                return [], SourceDiagnostic(
                    source=source.name,
                    job_count=0,
                    elapsed_seconds=monotonic() - started,
                    error=(
                        f"Джерело не відповіло за {self.source_timeout_seconds:g} с"
                    ),
                )
            except Exception as error:
                return [], SourceDiagnostic(
                    source=source.name,
                    job_count=0,
                    elapsed_seconds=monotonic() - started,
                    error=str(error),
                )

        async def run_with_progress(
            source: JobSource,
        ) -> tuple[list[JobPosting], SourceDiagnostic]:
            nonlocal completed_count, collected_count
            found, diagnostic = await run(source)
            completed_count += 1
            collected_count += len(found)
            if on_progress is not None:
                try:
                    on_progress(
                        diagnostic,
                        completed_count,
                        len(selected),
                        collected_count,
                    )
                except Exception:
                    # Progress reporting is observational and must never make a
                    # successful source search fail.
                    pass
            return found, diagnostic

        completed = await asyncio.gather(
            *(run_with_progress(source) for source in selected)
        )
        diagnostics = tuple(item[1] for item in completed)
        jobs = deduplicate_jobs(job for found, _ in completed for job in found)
        counts = {item.source: item.job_count for item in diagnostics}
        errors = {item.source: item.error for item in diagnostics if item.error}
        return SourceBatch(tuple(jobs), diagnostics, counts, errors)

    def search_sync(
        self,
        sources: Iterable[JobSource],
        query: SearchQuery,
        on_progress: Callable[[SourceDiagnostic, int, int, int], None] | None = None,
    ) -> SourceBatch:
        """Run the async orchestrator from CLI or a GUI worker thread."""
        return asyncio.run(self.search(sources, query, on_progress))


_T = TypeVar("_T")


async def _call_in_daemon_thread(
    function: Callable[[SearchQuery], _T],
    query: SearchQuery,
) -> _T:
    """Run blocking source code without waiting for it after a timeout."""

    loop = asyncio.get_running_loop()
    future: asyncio.Future[_T] = loop.create_future()

    def finish(result: _T | None = None, error: BaseException | None = None) -> None:
        if future.done():
            return
        if error is not None:
            future.set_exception(error)
        else:
            future.set_result(result)  # type: ignore[arg-type]

    def worker() -> None:
        try:
            result = function(query)
        except BaseException as error:
            try:
                loop.call_soon_threadsafe(finish, None, error)
            except RuntimeError:
                pass
        else:
            try:
                loop.call_soon_threadsafe(finish, result, None)
            except RuntimeError:
                pass

    threading.Thread(
        target=worker,
        name="jobcompass-source",
        daemon=True,
    ).start()
    return await future
