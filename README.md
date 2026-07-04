# finCard

Financial Microservice for high-reliability transaction processing.

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

The application automatically generates the database schema on startup via TortoiseORM (`generate_schemas=True`).

## Verifying the Application

### Important: Idempotency
This service implements **Idempotency**. If you send a request with a `transaction_id` that has already been processed, the system will return the **original record** from the database, even if you change other fields (like amount or currency). To process a new transaction, you must use a new, unique UUID.

You can test the transaction endpoint using `curl`:

```bash
curl -X 'POST' \
  'http://localhost:8000/transactions' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
  "amount": 150.50,
  "currency": "BRL"
}'
```

Check the health of the service:
```bash
curl http://localhost:8000/health
```

## Running Tests

To run the tests inside the container environment:

```bash
docker compose run api env PYTHONPATH=. pytest
```

### "ModuleNotFoundError: No module named 'distutils'"
If you see this error, it's because the old Python-based `docker-compose` (V1) is incompatible with Python 3.12.

**The Solution:** Use the modern Docker Compose V2 (included with Docker Desktop and modern Docker Engine), which is a plugin and doesn't depend on Python.

Use:
```bash
docker compose up --build
```
(Note the space instead of the hyphen).

### Summary of fixes:

1. **Use `docker compose` (V2):** Always prefer `docker compose` over `docker-compose`. V2 is written in Go and avoids all Python dependency issues.
2. **Explicit Network:** We have updated `docker-compose.yml` to use an explicit bridge network, as newer Docker versions can sometimes fail to auto-create default networks in specific environments.
3. **Command Syntax:**
   - Correct: `docker compose up`
   - Deprecated: `docker-compose up`
4. **Port Conflicts:** If you get "port already allocated" errors, try cleaning up existing containers:
   ```bash
   docker compose down
   docker compose up -d --force-recreate
   ```
5. **Variable Resolution:** Docker 29 is stricter about environment variables. If you use a `.env` file, ensure it is passed correctly:
   ```bash
   docker compose --env-file .env up -d
   ```

## Architecture

- **FastAPI:** Web framework with asynchronous support.
- **TortoiseORM:** Async ORM with PostgreSQL backend.
- **Celery + RabbitMQ:** Reliable background task processing for the Outbox pattern.
- **Redis:** Distributed locking for idempotency.
- **Prism (Mock Gateway):** Simulates the external payment gateway.

## Future Improvements: Reliability & Distributed Consistency

- **Try-Confirm-Cancel (TCC) Pattern:** Explore implementation of the TCC pattern for gateway interactions to ensure distributed consistency between the local database and external providers.
- **Change Data Capture (CDC):** Transition from a Celery-based outbox poller to a dedicated log tailing service (e.g., Debezium) that reads the PostgreSQL Write-Ahead Log (WAL) to guarantee delivery with lower database overhead.
- **Dead Letter Queues (DLQ):** Implement robust DLQ handling and automated retry mechanisms in RabbitMQ to manage failed event deliveries and enable easier manual interventions.
