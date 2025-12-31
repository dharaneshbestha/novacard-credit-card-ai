import time
from dataclasses import dataclass


@dataclass
class BreakerState:
    state: str = "CLOSED"  # CLOSED | OPEN | HALF_OPEN
    failures: int = 0
    last_failure_ts: float = 0.0
    opened_ts: float = 0.0
    next_half_open_try_ts: float = 0.0


class CircuitBreaker:
    def __init__(
        self,
        fail_threshold: int = 5,
        fail_window_seconds: int = 30,
        open_cooldown_seconds: int = 30,
        half_open_probe_seconds: int = 5,
    ):
        self.fail_threshold = fail_threshold
        self.fail_window_seconds = fail_window_seconds
        self.open_cooldown_seconds = open_cooldown_seconds
        self.half_open_probe_seconds = half_open_probe_seconds
        self.s = BreakerState()

    def allow(self) -> bool:
        now = time.time()

        if self.s.state == "CLOSED":
            return True

        if self.s.state == "OPEN":
            # cooldown expired -> try HALF_OPEN
            if (now - self.s.opened_ts) >= self.open_cooldown_seconds:
                self.s.state = "HALF_OPEN"
                self.s.next_half_open_try_ts = now
                return True
            return False

        # HALF_OPEN: allow one probe per interval
        if now >= self.s.next_half_open_try_ts:
            self.s.next_half_open_try_ts = now + self.half_open_probe_seconds
            return True
        return False

    def record_success(self):
        self.s.state = "CLOSED"
        self.s.failures = 0

    def record_failure(self):
        now = time.time()

        # reset window if last failure is old
        if (now - self.s.last_failure_ts) > self.fail_window_seconds:
            self.s.failures = 0

        self.s.failures += 1
        self.s.last_failure_ts = now

        if self.s.failures >= self.fail_threshold:
            self.s.state = "OPEN"
            self.s.opened_ts = now

    @property
    def state(self) -> str:
        return self.s.state
