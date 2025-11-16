from typing import Any, Dict, Optional

from ..models import PreValidation, Submission
from . import prevalidation_service


def run_pre_validation(
    submission: Submission,
    descriptor: Optional[Dict[str, Any]] = None,
    *,
    id_column: int | None = None,
    check_order: bool = False,
    **kwargs: Any,
) -> PreValidation:
    """
    Thin compatibility wrapper around ``prevalidation_service.run_prevalidation``.

    The legacy implementation duplicated the logic from ``prevalidation_service``
    but relied on fields that were removed from ``PreValidation``. To keep the
    public API stable (tests patch ``runner.services.validation_service.run_pre_validation``),
    we delegate the actual work to the battle-tested service.

    Parameters are accepted for backwards compatibility but currently unused —
    the descriptor info is already available via ``submission.problem.descriptor``.
    """
    return prevalidation_service.run_prevalidation(submission)
