import json

from django.conf import settings
from django_redis import get_redis_connection


class SeatLockService:
    """
    I centralize all Redis seat lock operations in this service.

    I use Redis as the source of truth for temporary locks because:
    - it supports expiration natively
    - it is fast
    - it prevents concurrent users from reserving the same seat
    """

    LOCK_PREFIX = "seat_lock"

    @classmethod
    def build_lock_key(cls, session_id: int, seat_id: int) -> str:
        """
        I generate a unique Redis key for one seat in one specific session.
        """
        return f"{cls.LOCK_PREFIX}:session:{session_id}:seat:{seat_id}"

    @classmethod
    def acquire_lock(cls, session_id: int, seat_id: int, user_id: int) -> bool:
        """
        I try to acquire a temporary lock for a seat.

        Redis SET with NX ensures the key is created only if it does not
        already exist. EX applies the lock expiration in seconds.

        I return:
        - True if the lock was successfully created
        - False if the seat is already locked
        """
        redis_conn = get_redis_connection("default")
        lock_key = cls.build_lock_key(session_id=session_id, seat_id=seat_id)

        payload = json.dumps({
            "user_id": user_id,
            "session_id": session_id,
            "seat_id": seat_id,
        })

        result = redis_conn.set(
            lock_key,
            payload,
            nx=True,
            ex=settings.SEAT_LOCK_TIMEOUT,
        )

        return bool(result)

    @classmethod
    def get_lock_data(cls, session_id: int, seat_id: int):
        """
        I return the stored Redis payload for a lock, if it exists.
        """
        redis_conn = get_redis_connection("default")
        lock_key = cls.build_lock_key(session_id=session_id, seat_id=seat_id)

        value = redis_conn.get(lock_key)
        if not value:
            return None

        if isinstance(value, bytes):
            value = value.decode("utf-8")

        return json.loads(value)

    @classmethod
    def get_lock_ttl(cls, session_id: int, seat_id: int) -> int:
        """
        I return the remaining TTL in seconds for a seat lock.

        Redis returns:
        - positive integer: remaining TTL
        - -1: key exists but has no expiration
        - -2: key does not exist
        """
        redis_conn = get_redis_connection("default")
        lock_key = cls.build_lock_key(session_id=session_id, seat_id=seat_id)
        return redis_conn.ttl(lock_key)

    @classmethod
    def release_lock(cls, session_id: int, seat_id: int, user_id: int) -> bool:
        """
        I release a lock only if it belongs to the informed user.

        This avoids allowing one user to delete another user's lock.
        """
        redis_conn = get_redis_connection("default")
        lock_key = cls.build_lock_key(session_id=session_id, seat_id=seat_id)

        lock_data = cls.get_lock_data(session_id=session_id, seat_id=seat_id)
        if not lock_data:
            return False

        if lock_data.get("user_id") != user_id:
            return False

        deleted = redis_conn.delete(lock_key)
        return bool(deleted)

    @classmethod
    def list_reserved_seat_ids_for_session(cls, session_id: int) -> set:
        """
        I scan Redis keys for one session and return all locked seat IDs.

        This is useful for CASE 4, where I need to mark seats as RESERVED
        in the seat map response.
        """
        redis_conn = get_redis_connection("default")
        pattern = f"{cls.LOCK_PREFIX}:session:{session_id}:seat:*"

        seat_ids = set()
        for key in redis_conn.scan_iter(match=pattern):
            if isinstance(key, bytes):
                key = key.decode("utf-8")

            try:
                seat_id = int(key.split(":")[-1])
                seat_ids.add(seat_id)
            except (ValueError, IndexError):
                continue

        return seat_ids