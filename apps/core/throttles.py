from rest_framework.throttling import ScopedRateThrottle


class LoginRateThrottle(ScopedRateThrottle):
    """
    I apply a stricter rate limit to login attempts to reduce brute-force abuse.
    """

    scope = "login"


class RegisterRateThrottle(ScopedRateThrottle):
    """
    I apply a stricter rate limit to user registration attempts.
    """

    scope = "register"


class SeatReserveRateThrottle(ScopedRateThrottle):
    """
    I limit how often a user can attempt to reserve seats.
    """

    scope = "seat_reserve"


class SeatCheckoutRateThrottle(ScopedRateThrottle):
    """
    I limit how often a user can attempt to checkout seats.
    """

    scope = "seat_checkout"