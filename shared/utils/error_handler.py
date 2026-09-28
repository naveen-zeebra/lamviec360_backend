# ─────────────────────────────────────────────────────────────────────────────
# File    : shared/utils/error_handler.py
# Purpose : Centralized error handling decorator for service layer operations
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import functools
import inspect
import traceback
import typing
from typing import Union, get_args, get_origin
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from shared.utils.logger import get_logger

logger = get_logger("service_error_handler")


def _get_fallback(annotation) -> object:
    """Return a safe default value based on the function's return type annotation."""
    if annotation is inspect.Parameter.empty or annotation is None:
        return None

    origin = get_origin(annotation)

    if origin is Union:
        return None

    if annotation is list or origin is list:
        return []

    if annotation is dict or origin is dict:
        return {}

    if annotation is bool:
        return False

    if annotation is str:
        return ""

    if annotation is int:
        return 0

    return None


def service_error_handler(func):
    """
    Decorator for service layer functions.
    On any unhandled exception:
      1. Re-raises HTTPException and ValueError so callers handle domain errors.
      2. Logs the error + full traceback.
      3. Rolls back the SQLAlchemy session if db is present in arguments.
      4. Returns a safe fallback value based on return type annotation.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except ValueError:
            raise

        except HTTPException:
            raise

        except (IntegrityError, SQLAlchemyError):
            raise

        except Exception as exc:
            tb = traceback.format_exc()
            logger.error(f"[SERVICE ERROR] {func.__name__} | error={type(exc).__name__}: {exc} | traceback={tb}")

            # Roll back DB session if passed in arguments
            for arg in list(args) + list(kwargs.values()):
                if isinstance(arg, Session):
                    try:
                        arg.rollback()
                        logger.warning(f"[DB ROLLBACK] {func.__name__} | session rolled back after error")
                    except Exception:
                        pass
                    break

            try:
                return_annotation = typing.get_type_hints(func).get('return', inspect.Signature.empty)
            except Exception:
                return_annotation = inspect.signature(func).return_annotation

            return _get_fallback(return_annotation)

    return wrapper
