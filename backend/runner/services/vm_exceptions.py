class VmError(Exception):
    """Base exception for VM orchestration errors."""


class VmAlreadyExistsError(VmError):
    """Raised when attempting to create an already existing VM."""


class VmNotFoundError(VmError):
    """Raised when a VM cannot be located."""


__all__ = ["VmError", "VmAlreadyExistsError", "VmNotFoundError"]
