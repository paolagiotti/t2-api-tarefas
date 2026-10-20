import logging
from contextvars import ContextVar

LOG_FORMAT = "%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s"
HANDLER_NAME = "app"

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Inclui o identificador da requisição atual em todos os registros de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.set_name(HANDLER_NAME)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root = logging.getLogger()
    for existing in list(root.handlers):
        if existing.get_name() == HANDLER_NAME:
            root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level.upper())
