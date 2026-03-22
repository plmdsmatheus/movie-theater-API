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
git clone https://github.com/plmdsmatheus/movie-theater-API.git
cd movie-theater-API
```

## 2. Create the .env file

```bash
SECRET_KEY=
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=cinepolis_db
DB_USER=cinepolis_user
DB_PASSWORD=
DB_HOST=db
DB_PORT=5432

REDIS_URL=redis://redis:6379/1

SEAT_LOCK_TIMEOUT=600

MOVIES_LIST_CACHE_TTL=300
MOVIE_SESSIONS_CACHE_TTL=120
```

## 3. Upload Container

```bash
docker compose up --build
```

## 4. Run Migrations

```bash
docker compose exec web poetry run python manage.py migrate
```

## 5. Seed
Run the seed to populate the database

```bash
docker compose exec web poetry run python manage.py seed_data
```

## API documentation
Swagger is available at ```http://localhost:8000/api/schema/swagger-ui/```

---

# 🔑 Authentication
Login

```bash
POST /api/auth/login/
```
Refresh Token

```bash
POST /api/auth/refresh/
```
# 🎯 Key endpoints
### 🎬 Movies

```bash
GET /api/movies/
```
Lists all available movies.

### 🎥 Sessions

```bash
GET /api/movies/{movie_id}/sessions/
```
List of upcoming sessions for a movie.

### 💺 Seat Map

```bash
GET /api/sessions/{session_id}/seat-map/
```
Returns a seating chart with the following statuses:

- AVAILABLE
- RESERVED
- PURCHASED

### 🔒 Reserve Seat

```bash
POST /api/sessions/{session_id}/reserve-seat/
```

Creates a temporary lock (Redis - 10 minutes)

### 🛒 Checkout

```bash
POST /api/sessions/{session_id}/checkout/
```
- validate lock
- create ticket
- remove lock
- trigger asynchronous task (email)

### 🎟 My Tickets

```bash
GET /api/my-tickets/
GET /api/my-tickets/?type=active
GET /api/my-tickets/?type=history
```
---
# Pagination
All listing endpoints use pagination:
```JSON
{
  "count": 100,
  "next": "...",
  "previous": null,
  "results": []
}
```
Available parameters:
```JSON
?page=1
?page_size=10
```
---

# ⚙️ CI/CD 
Pipeline with GitHub Actions:
- installs dependencies using Poetry
- runs migrations
- runs automated tests
Runs on:
- every push
- every pull request
---

# 🧪 Tests
Run locally:
```bash
docker compose exec web poetry run python manage.py test
```
Coverage includes:
- authentication
- listings
- seat reservations
- checkout
- business rules
- edge cases
---
# ⚡ Celery

Available services:
- celery_worker
- celery_beat

Logs:

```bash
docker compose logs -f celery_worker
```
