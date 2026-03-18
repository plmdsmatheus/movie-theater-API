# 🎬 Movie Theater's tickets API

RESTful API for managing movie showtimes, seat reservations, and issuing digital tickets.

This project was developed as part of B2BIT's technical selection process, using **Django REST Framework**, **PostgreSQL**, **Redis**, and **Celery**.

---

# 🚀 Technologies Used

- Python 3.10+
- Django + Django REST Framework
- PostgreSQL
- Redis
- Celery (worker + beat)
- JWT Authentication (SimpleJWT)
- Docker & Docker Compose
- Poetry (dependency management)
- DRF Spectacular (Swagger)
- GitHub Actions (CI)

---

# 📦 Architecture

The application follows a modular, app-based architecture:

apps/<br>
- users/  # authentication and users<br>
- movies/ # main section (movies, session, seats, tickets)<br>
- core/  # shared utilities (pagination, throttling, caching)<br>

## 🔁 Main stream

1. User logs in (JWT)
2. Views movie listings and showtimes
3. Views the seating chart
4. Reserves a seat (Redis lock)
5. Proceeds to checkout
6. Ticket is generated
7. Email is sent via Celery
8. User accesses “My Tickets”

---

# 🔐 Security

- JWT Authentication
- Rate limiting with DRF Throttling
- Input validation with serializers
- Django ORM (protection against SQL injection)
- Permission control by endpoint

---

# ⚡ Scalability

- Redis as a **distributed lock** for reservations
- Cache for high-read endpoints:
  - movie list
  - showtimes per movie
- Mandatory pagination on listing endpoints

---

# 🔁 Asynchrony

Using **Celery + Redis**:

- sending ticket confirmation emails
- periodic tasks with `celery beat`

---

# 🐳 How to run the project (Docker)

## 1. Clone the repository

```bash
git clone https://github.com/seu-usuario/cinepolis-natal-api.git
cd cinepolis-natal-api

## 2. Crie o .env
```bash
SECRET_KEY=your-secret-key
DEBUG=True

DB_NAME=cinepolis_db
DB_USER=cinepolis_user
DB_PASSWORD=cinepolis_password
DB_HOST=db
DB_PORT=5432

REDIS_URL=redis://redis:6379/1

