# Credit Approval System

A backend system for credit approval handling customer registration, loan eligibility checks, and loan processing. Built with Django and Django REST Framework, utilizing Celery and Redis for asynchronous data ingestion.

## Tech Stack

*   **Django 4.2 & DRF**: API development
*   **PostgreSQL**: Relational database
*   **Celery & Redis**: Background task processing
*   **Docker**: Containerization

## Features

*   **Customer Registration**: registers users and calculates approved credit limits.
*   **Eligibility Check**: Evaluates loan eligibility based on credit score.
*   **Loan Processing**: Creates and manages loans with EMI calculations.
*   **Data Ingestion**: Background tasks to import customer and loan data from Excel.
*   **Decimal Precision**: Financial calculations use exact decimal arithmetic.
*   **Concurrency Handling**: Atomic transactions and row locking for data integrity.

## Business Logic Overview

The system calculates a credit score (0-100) based on:
1.  Past loan repayment history.
2.  Number of active loans.
3.  Loan activity in the current year.
4.  Loan approved volume.

**Approval Slabs:**
*   **Score > 50**: Approved.
*   **Score 50-30**: Approved if interest rate > 12%.
*   **Score 30-10**: Approved if interest rate > 16%.
*   **Score < 10**: Rejected.

EMIs are calculated using the compound interest formula. Total EMIs cannot exceed 50% of monthly salary.

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/register` | Register a new customer |
| `POST` | `/api/check-eligibility` | Check loan eligibility |
| `POST` | `/api/create-loan` | Create a new loan |
| `GET` | `/api/view-loan/<id>` | View loan details |
| `GET` | `/api/view-loans/<customer_id>` | View all loans for a customer |
| `POST` | `/api/ingest-data` | Trigger background data ingestion |

## Running the Project

Ensure Docker and Docker Compose are installed.

1.  **Clone and Start**
    ```bash
    git clone https://github.com/RAHUKKRRANJAN/credit-approval-system.git
    cd credit-approval-system
    docker-compose up --build

    ```

2.  **Ingest Data**
    Once the server is running (port 8000), trigger the data ingestion:
    ```bash
    curl -X POST http://localhost:8000/api/ingest-data
    ```

## Environment Variables

Configuration is managed via the `.env` file:

*   `DJANGO_SECRET_KEY`: Django security key.
*   `DEBUG`: Debug mode (False for production).
*   `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: Database credentials.
*   `CELERY_BROKER_URL`: Redis connection string.
*   `API_KEYS`: Comma-separated list of valid API keys for authentication.

## Running Tests

The project includes a comprehensive test suite covering models, services, and APIs.

```bash
docker-compose exec web python manage.py test
```

## Notes

*   **Authentication**: The system uses `X-API-KEY` header for authentication on all endpoints except health checks.
*   **Concurrency**: Critical sections like loan creation utilize database locking (`select_for_update`) to prevent race conditions.

