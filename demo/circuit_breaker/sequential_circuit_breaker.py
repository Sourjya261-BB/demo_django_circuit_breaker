from asyncio import iscoroutinefunction
from collections import deque
from datetime import datetime, timedelta
from functools import wraps
from inspect import isclass
from time import monotonic


STRING_TYPES = (bytes, str)
STATE_CLOSED = 'closed'
STATE_OPEN = 'open'
STATE_HALF_OPEN = 'half_open'

def in_exception_list(*exc_types):
    """Build a predicate function that checks if an exception is a subtype from a list"""

    def matches_types(thrown_type, _):
        return issubclass(thrown_type, exc_types)

    return matches_types


def build_failure_predicate(expected_exception):
    """ Build a failure predicate_function.
          The returned function has the signature (Type[Exception], Exception) -> bool.
          Return value True indicates a failure in the underlying function.

        :param expected_exception: either an type of Exception, iterable of Exception types, or a predicate function.

          If an Exception type or iterable of Exception types, the failure predicate will return True when a thrown
          exception type matches one of the provided types.

          If a predicate function, it will just be returned as is.

         :return: callable (Type[Exception], Exception) -> bool
    """

    if isclass(expected_exception) and issubclass(expected_exception, Exception):
        failure_predicate = in_exception_list(expected_exception)
    else:
        try:
            # Check for an iterable of Exception types
            iter(expected_exception)

            # guard against a surprise later
            if isinstance(expected_exception, STRING_TYPES):
                raise ValueError("expected_exception cannot be a string. Did you mean name?")
            failure_predicate = in_exception_list(*expected_exception)
        except TypeError:
            # not iterable. guess that it's a predicate function
            if not callable(expected_exception) or isclass(expected_exception):
                raise ValueError("expected_exception does not look like a predicate")
            failure_predicate = expected_exception
    return failure_predicate

class CircuitBreaker:
    FAILURE_THRESHOLD = 50  # Percentage of failures to transition to open
    WINDOW_SIZE = 30  # Sliding window size in seconds
    RECOVERY_TIMEOUT = 30  # Open state duration before moving to half-open
    HALF_OPEN_PERIOD = 5  # Duration to monitor requests in half-open state
    EXPECTED_EXCEPTION = Exception

    def __init__(self,
                 failure_threshold=None,
                 window_size=None,
                 recovery_timeout=None,
                 half_open_period=None,
                 expected_exception=None,
                 name=None,
                 fallback_function=None):
        self._failure_threshold = failure_threshold or self.FAILURE_THRESHOLD
        self._window_size = window_size or self.WINDOW_SIZE
        self._recovery_timeout = recovery_timeout or self.RECOVERY_TIMEOUT
        self._half_open_period = half_open_period or self.HALF_OPEN_PERIOD
        self._name = name
        self._previous_state = None
        self._fallback_function = fallback_function

        # Time-based sliding window
        self._events = deque()
        self._state = STATE_CLOSED
        self._last_transition = monotonic()
        self.is_failure = build_failure_predicate(expected_exception or self.EXPECTED_EXCEPTION)

    def _record_event(self, success: bool):
        now = monotonic()
        self._events.append((now, success))
        self._cleanup_old_events()
    # def _record_event(self, success: bool):
    #     now = monotonic()
    #     self._events.append((now, success))
    #     self._cleanup_old_events()
    #
    #     # Evaluate state transition only if sufficient time has elapsed
    #     elapsed_time = now - self._last_transition
    #     if elapsed_time >= self._window_size:
    #         self._evaluate_closed_state()

    def _cleanup_old_events(self):
        cutoff = monotonic() - self._window_size
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    def _failure_rate(self):
        if not self._events:
            return 0
        failures = sum(1 for _, success in self._events if not success)
        return (failures / len(self._events)) * 100

    def _transition_to(self, new_state):
        self._previous_state = self._state  # Store the current state as the previous state
        self._state = new_state
        self._last_transition = monotonic()

    def _handle_open_state(self):
        """
        Called when the circuit transitions to the OPEN state.
        Executes the fallback function, if provided.
        """
        if self._fallback_function:
            self._fallback_function()

    def _check_half_open(self):
        now = monotonic()
        if now - self._last_transition >= self._half_open_period:
            failure_rate = self._failure_rate()
            if failure_rate <= self._failure_threshold:
                self._transition_to(STATE_CLOSED)
            else:
                self._transition_to(STATE_OPEN)
        else:
            # If still in the half-open period and previous state was OPEN, update previous state
            if self._previous_state == STATE_OPEN:
                self._previous_state = STATE_HALF_OPEN

    def call(self, func, *args, **kwargs):
        """
        Calls the decorated function and applies circuit breaker rules.
        """
        if self._state == STATE_OPEN:
            if monotonic() - self._last_transition >= self._recovery_timeout:
                self._transition_to(STATE_HALF_OPEN)

            # else:
            #     raise CircuitBreakerError(self)
            else:
                # If the circuit breaker was CLOSED before opening, update the previous state
                if self._previous_state == STATE_CLOSED:
                    self._previous_state = STATE_OPEN  # Update the previous state
                    raise CircuitBreakerError(self)
                elif self._previous_state == STATE_HALF_OPEN:
                    self._previous_state = STATE_HALF_OPEN  # Update the previous state
                    raise CircuitBreakerError(self)
                else:
                    raise CircuitBreakerError(self)

        if self._state == STATE_HALF_OPEN:
            self._check_half_open()

        try:
            result = func(*args, **kwargs)
            self._record_event(success=True)
            return result
        except Exception as ex:
            if self.is_failure(type(ex), ex):
                self._record_event(success=False)
                if self._state == STATE_CLOSED and self._failure_rate() > self._failure_threshold and monotonic()-self._last_transition>=self._window_size:
                    self._transition_to(STATE_OPEN)
                if self._state == STATE_CLOSED and monotonic()-self._last_transition<self._window_size:
                    if self._previous_state==STATE_HALF_OPEN:
                        self._previous_state = STATE_CLOSED
                elif self._state == STATE_HALF_OPEN:
                    self._check_half_open()
            raise

    @property
    def state(self):
        return self._state

    @property
    def failure_rate(self):
        return self._failure_rate()

    @property
    def open_until(self):
        if self._state != STATE_OPEN:
            return None
        return datetime.utcnow() + timedelta(seconds=self._recovery_timeout)

    @property
    def previous_state(self):
        return self._previous_state

    @property
    def name(self):
        return self._name

    def __str__(self):
        return f"{self._name} (state={self._state}, failure_rate={self.failure_rate:.2f}%)"

class CircuitBreakerError(Exception):
    def __init__(self, circuit_breaker, *args, **kwargs):
        """
        :param circuit_breaker: The circuit breaker instance that raised the error
        :param args: Positional arguments for the Exception base class
        :param kwargs: Keyword arguments for the Exception base class
        """
        super().__init__(*args, **kwargs)
        self._circuit_breaker = circuit_breaker

    def __str__(self, *args, **kwargs):
        """
        String representation of the CircuitBreakerError, providing detailed information.
        """
        return (
            f'**--Circuit Breaker Error has been triggered for connection:{self._circuit_breaker.name},window_size:{self._circuit_breaker._window_size},recovery_timeout:{self._circuit_breaker._recovery_timeout},failure_threshold:{self._circuit_breaker._failure_threshold}%,current_failure_percentage:{self._circuit_breaker.failure_rate}--**'
        )
