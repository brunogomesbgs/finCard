# finCard

Financial Microservice for high-reliability transaction processing with CQRS and Event Sourcing.

## Architecture

This project follows a modern architecture focused on reliability, auditability, and scalability:

- **CQRS (Command Query Responsibility Segregation):** Separation of write operations (Commands) and read operations (Queries) to optimize performance and scalability.
- **Event Sourcing:** All state changes are stored as a sequence of immutable events in the `event_store`. The current state (Read Model) is a projection of these events.
- **Repository Pattern:** Abstracted database access layer for better testability and separation of concerns.
- **TCC (Try-Confirm-Cancel) Pattern:** Distributed consistency managed through explicit phases (Try: create record, Confirm: external gateway call, Cancel: mark as failure on error).
- **Outbox Pattern (Decoupled):** Ensures reliable message delivery to RabbitMQ. Polling is handled by a background Celery Beat worker to reduce API latency.
- **Dead Letter Queues (DLQ):** RabbitMQ configured with DLQs to handle and audit failed message deliveries.
- **JWT Authentication:** Secure access control with Role-Based Access Control (RBAC) for `USER` and `ADMIN` roles. Handles high-security password hashing with SHA-256 pre-hashing for bcrypt compatibility.
- **FastAPI:** High-performance asynchronous web framework.
- **TortoiseORM:** Async ORM with PostgreSQL backend.
- **Celery + RabbitMQ:** Background task processing for outbox events and decoupled polling.
- **Redis:** Distributed locking for transaction idempotency.
- **Self-Healing Database:** Automatic schema migration and maintenance during startup.

## Database Schema (Event Store)

The `event_store` table is the source of truth for all domain changes:

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `uuid` | Unique event identifier. |
| `aggregate_type` | `varchar(50)` | The type of the aggregate (e.g., "User", "Transaction"). |
| `aggregate_id` | `uuid` | The unique ID of the aggregate. |
| `event_type` | `varchar(100)` | The type of event (e.g., "UserCreated", "TransactionProcessed"). |
| `payload` | `jsonb` | The data associated with the event. |
| `payload_version` | `smallint` | Version of the payload schema. |
| `occurred_at` | `timestamptz` | When the event actually happened. |
| `recorded_at` | `timestamptz` | When the event was recorded in the database. |
| `sequence` | `bigint` | Ordered sequence for the aggregate events. |
| `actor_id` | `uuid` | The ID of the user/system that performed the action. |
| `actor_type` | `varchar(20)` | Type of the actor ("USER", "SYSTEM"). |
| `correlation_id` | `uuid` | ID to trace requests across multiple services. |
| `is_anonymized` | `boolean` | Flag for data privacy compliance. |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Running Locally

To start the entire stack (API, Database, Redis, RabbitMQ, Worker, and a Mock Gateway):

```bash
docker compose up --build
```

The application will be available at:
- **API:** [http://localhost:8000](http://localhost:8000)
- **Swagger Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **RabbitMQ Management:** [http://localhost:15672](http://localhost:15672) (guest/guest)

### Initialization

The application automatically generates the database schema on startup via TortoiseORM. It also includes a self-healing mechanism to ensure legacy tables are updated to the latest schema requirements.

## Authentication & Authorization

All transaction endpoints require a valid JWT token.

### User Roles
- **USER:** Can create transactions, list their own transactions, and update their profile.
- **ADMIN:** Can list all transactions and list all users in the system.

### Auth Flows

1.  **Register:** `POST /users` (Create user with `email`, `name`, `password` [min 6 chars], `role`).
2.  **Login:** `POST /token` (Standard OAuth2 password flow).
3.  **Update Password:** `PUT /users/password` (Requires current password and new password).
4.  **Update Profile:** `PUT /users/me` (Change name or email).
5.  **List Users:** `GET /users` (ADMIN only).

## Verifying the Application

### 1. Create a User
```bash
curl -X 'POST' \
  'http://localhost:8000/users' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "user@example.com",
  "name": "John Doe",
  "password": "securepassword123",
  "role": "USER"
}'
```

### 2. Login
```bash
TOKEN=$(curl -s -X 'POST' \
  'http://localhost:8000/token' \
  -d 'username=user@example.com&password=securepassword123' \
  | jq -r .access_token)
```

### 3. Create Transaction
```bash
curl -X 'POST' \
  'http://localhost:8000/transactions' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "amount": 150.50,
  "currency": "BRL"
}'
```

### Idempotency
This service implements **Idempotency**. If you send a request with a `transaction_id` that has already been processed, the system will return the **original record**. To process a new transaction, you must use a new, unique UUID.

## Verifying the Architecture

1.  **Repository Pattern:** Check `app/infrastructure/repositories/base.py` for abstracted DB access.
2.  **TCC Flow:** Review `app/application/service.py` `process_transaction` method for Try/Confirm/Cancel logic.
3.  **Decoupled Outbox:** Observe that `app/interfaces/api/endpoints.py` no longer calls the publisher synchronously. Polling is now in `app/infrastructure/messaging/tasks.py` and scheduled in `app/infrastructure/messaging/worker.py`.
4.  **DLQ:** Check `app/infrastructure/messaging/worker.py` for RabbitMQ queue arguments defining the Dead Letter Exchange.
5.  **CQRS & ES:** Verify `event_store` table and Event Sourcing logic in `app/application/events/store.py`.

## Running Tests

To run the tests inside the container environment:

```bash
docker compose run api env PYTHONPATH=. pytest
```
