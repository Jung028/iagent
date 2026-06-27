import logging
import os

import structlog


def _add_service(_logger, _method_name, event_dict):
    # Static field so log shippers / Loki can identify the source service.
    event_dict.setdefault("service", "iagent")
    return event_dict


def configure_logging() -> None:
    # Always log JSON to stdout; also write to a file so promtail can scrape it
    # into Loki (the file dir is mounted to /var/log/iagent in the promtail
    # container). File logging is best-effort — never fail startup over it.
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    log_dir = os.environ.get("LOG_DIR", "logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
        handlers.append(logging.FileHandler(os.path.join(log_dir, "iagent.log")))
    except OSError:
        pass

    # Use stdlib logger factory so add_logger_name can read logger.name
    logging.basicConfig(format="%(message)s", level=logging.INFO, handlers=handlers)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_service,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
