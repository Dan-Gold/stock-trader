"""Exception handlers for the Stock Trader API."""

import logging
import traceback
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from stock_trader.models.exceptions import JobNotFoundException

logger = logging.getLogger(__name__)


SIMPLE_EXCEPTION_HANDLERS: dict[type[Exception], int] = {
    ValueError: status.HTTP_400_BAD_REQUEST,
    JobNotFoundException: status.HTTP_404_NOT_FOUND,
}

TRACEBACK_EXCEPTION_HANDLERS: dict[type[Exception], int] = {
    NotImplementedError: status.HTTP_501_NOT_IMPLEMENTED,
}

FORMATTED_EXCEPTION_HANDLERS: dict[type[Exception], tuple[int, str]] = {
    KeyError: (status.HTTP_404_NOT_FOUND, "A required key is missing: {exception!s}"),
}


def add_exception_handlers(app: FastAPI) -> None:
    """Add exception handlers to the FastAPI app.

    Args:
        app: The FastAPI application instance.
    """
    # Generic handler for unexpected exceptions
    app.add_exception_handler(
        Exception,
        create_formatted_exception_handler(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "An unexpected error occurred: {exception!s}",
            include_traceback=True,
        ),
    )

    # Simple handlers
    for exception_type, status_code in SIMPLE_EXCEPTION_HANDLERS.items():
        app.add_exception_handler(
            exception_type,
            create_simple_exception_handler(status_code),
        )

    # Handlers with traceback
    for exception_type, status_code in TRACEBACK_EXCEPTION_HANDLERS.items():
        app.add_exception_handler(
            exception_type,
            create_simple_exception_handler(status_code, include_traceback=True),
        )

    # Formatted message handlers
    for exception_type, (status_code, message_template) in FORMATTED_EXCEPTION_HANDLERS.items():
        app.add_exception_handler(
            exception_type,
            create_formatted_exception_handler(
                status_code,
                message_template,
            ),
        )


def create_formatted_exception_handler(
    status_code: int,
    message_template: str,
    include_traceback: bool = False,
) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    """Factory to create a formatted exception handler.

    Args:
        status_code: The HTTP status code to return.
        message_template: The message template for the exception.
        include_traceback: Whether to include the traceback in the response.

    Returns:
        A FastAPI exception handler function.
    """

    async def handler(request: Request, exception: Exception) -> JSONResponse:
        logger.exception("Handled exception: %s", exception)

        if include_traceback:
            logger.error("Traceback:\n%s", traceback.format_exc())

        return JSONResponse(
            status_code=status_code,
            content={"detail": message_template.format(exception=exception)},
        )

    return handler


def create_simple_exception_handler(
    status_code: int, include_traceback: bool = False
) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    """Factory to create a simple exception handler.

    Args:
        status_code: The HTTP status code to return.
        include_traceback: Whether to include the traceback in the response.

    Returns:
        A FastAPI exception handler function.
    """

    async def handler(request: Request, exception: Exception) -> JSONResponse:
        logger.exception("Handled exception: %s", exception)

        if include_traceback:
            logger.error("Traceback:\n%s", traceback.format_exc())

        return JSONResponse(
            status_code=status_code,
            content={"detail": str(exception)},
        )

    return handler
