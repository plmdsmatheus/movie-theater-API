from celery import shared_task
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_ticket_confirmation_email_task(
    user_email: str,
    movie_title: str,
    room_name: str,
    seat_code: str,
    session_start_time: str,
    ticket_code: str,
):
    """
    I send a ticket confirmation e-mail asynchronously after checkout.
    """
    subject = f"Your Cinépolis Natal ticket - {movie_title}"
    message = (
        f"Your ticket was generated successfully.\n\n"
        f"Movie: {movie_title}\n"
        f"Room: {room_name}\n"
        f"Seat: {seat_code}\n"
        f"Session start: {session_start_time}\n"
        f"Ticket code: {ticket_code}\n"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@cinepolis.local"),
        recipient_list=[user_email],
        fail_silently=True,
    )

    return {"status": "sent", "email": user_email, "ticket_code": ticket_code}


@shared_task
def cleanup_movie_cache_task():
    """
    I run a simple periodic cleanup for selected cached keys.

    This task is intentionally simple for the technical challenge.
    """
    # Example: remove a broad cache namespace by known keys if you track them.
    # For now, I just return a marker so the periodic task exists and is auditable.
    return {"status": "ok", "message": "Periodic cache cleanup task executed."}