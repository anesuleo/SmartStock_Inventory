# SmartStock_Inventory

The core backend service for SmartStock — an AI-powered inventory and demand forecasting system built for pharmaceutical and warehouse stock management.

This repository contains the REST API that all other SmartStock services depend on. It handles inventory records, stock movements, and barcode scanning, and is the central data source for the forecasting and frontend layers.

## What it does

- Full CRUD API for managing pharmaceutical inventory items
- Tracks every stock movement (items received and items dispensed) as a ledger
- Barcode scanning endpoint that accepts scans from an Arduino-connected barcode reader and looks up the matching inventory item in real time
- Multi-environment support — runs locally with SQLite for development, and PostgreSQL in Docker for production
- Deployed on AWS EC2 via Docker, exposed externally through ngrok
- Automated testing with pytest and CI via GitHub Actions

## Tech Stack

- **Python / FastAPI** — REST API framework
- **PostgreSQL** — production database
- **SQLAlchemy** — ORM (database access layer)
- **Docker / Docker Compose** — containerisation and local production environment
- **AWS EC2** — cloud deployment
- **pytest** — automated testing
- **GitHub Actions** — continuous integration

## Project Structure
app/
main.py         # All API routes
models.py       # Database table definitions
schemas.py      # Request/response validation
database.py     # Database connection and session management
barcode.py      # Serial listener for Arduino barcode scanner
seed.py         # Script to populate the database with test data
tests/            # pytest test suite
.github/workflows/ci.yml  # GitHub Actions CI pipeline
docker-compose.yml
Dockerfile
## Running Locally

**Requirements:** Python 3.11+, Docker (for PostgreSQL mode)

```bash
# Install dependencies
pip install -r requirements.txt

# Run in dev mode (SQLite)
make run

# Run tests
make test

# Run with Docker (PostgreSQL)
docker compose up --build
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/inventory` | List all inventory items |
| POST | `/api/inventory` | Add a new item |
| GET | `/api/inventory/{id}` | Get a single item |
| PUT | `/api/inventory/{id}` | Replace an item |
| PATCH | `/api/inventory/{id}` | Partially update an item |
| DELETE | `/api/inventory/{id}` | Delete an item |
| POST | `/api/inventory/scan` | Look up an item by barcode |
| POST | `/api/inventory/{id}/movement` | Record a stock IN or OUT movement |
| GET | `/api/movements` | List all stock movements |
| GET | `/api/sales` | List all outgoing (OUT) movements |

## Related Repositories

| Repository | Description |
|------------|-------------|
| [SmartStock_Frontend](https://github.com/anesuleo/SmartStock_Frontend) | Desktop GUI built with CustomTkinter |
| [SmartStock_Authentication](https://github.com/anesuleo/SmartStock_Authentication) | Session-based authentication service |
| [SmartStock_Forecasting](https://github.com/anesuleo/SmartStock_Forecasting) | Demand forecasting and stockout risk prediction |
| [SmartStock_Deployment](https://github.com/anesuleo/SmartStock_Deployment) | Backend Deployment repository |

