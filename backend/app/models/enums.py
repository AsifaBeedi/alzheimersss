import enum


class EventType(str, enum.Enum):
    WANDERING_EPISODE = "wandering_episode"
    WRONG_TURN = "wrong_turn"
    FALL = "fall"
    AGITATION = "agitation"


class Severity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, enum.Enum):
    WANDERING = "wandering"
    LOW_ADHERENCE = "low_adherence"
    LOW_INDEPENDENCE = "low_independence"
    FALL = "fall"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
