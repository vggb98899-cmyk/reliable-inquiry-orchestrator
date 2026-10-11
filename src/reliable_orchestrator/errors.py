class OrchestrationError(RuntimeError):
    """Base class for deterministic orchestration failures."""


class SnapshotExpired(OrchestrationError):
    pass


class SchemaMismatch(OrchestrationError):
    pass


class TargetMismatch(OrchestrationError):
    pass


class DuplicateBusinessKey(OrchestrationError):
    pass


class BlastRadiusExceeded(OrchestrationError):
    pass


class UnknownSideEffect(OrchestrationError):
    pass


class LeaseUnavailable(OrchestrationError):
    pass


class ReadbackMismatch(OrchestrationError):
    pass
