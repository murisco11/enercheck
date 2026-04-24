import asyncio
import logging

from src.app.dependencies import get_container
from src.modules.ai_demo.application.use_cases import AIDemoService

logger = logging.getLogger(__name__)


async def process_event(service: AIDemoService, event_name: str, payload: dict[str, str]) -> None:
    if event_name != "ai_demo.requested":
        logger.warning("worker.event_ignored", extra={"event_name": event_name})
        return

    result = await service.respond(payload["message"])
    logger.info(
        "worker.ai_demo_processed",
        extra={
            "job_id": payload["job_id"],
            "provider": result.provider,
        },
    )


async def run_worker(iterations: int | None = None) -> None:
    container = get_container()
    poll_interval = container.settings.worker_poll_interval_seconds
    processed = 0

    while iterations is None or processed < iterations:
        envelope = await container.message_consumer.consume()
        if envelope is None:
            await asyncio.sleep(poll_interval)
            continue

        await process_event(container.ai_demo_service, envelope.event_name, envelope.payload)
        processed += 1


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
