# Wallet Service API

A production-ready backend wallet service featuring Paystack payment integration, Google OAuth authentication, and granular permission-based API key management. Built with ACID-compliant transactions, idempotency guarantees, and comprehensive security controls.

## Tech Stack

- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL 16 (async SQLAlchemy + SQLModel)
- **Cache**: Redis 7
- **Reverse Proxy**: Nginx
- **Authentication**: JWT + API Keys
- **Payment**: Paystack
- **Logging**: Python logging (stdout + file)

## Project Structure

```
hngx13-stage-8-backend/
├── main.py                     # FastAPI app entry point
├── config.py                   # Settings (pydantic-settings)
├── start.sh                    # Startup script
├── Dockerfile                  # API container
├── docker-compose.yml          # Multi-container setup (db, redis, api, nginx)
├── requirements.txt            # Python dependencies
│
├── app/api/
│   ├── core/
│   │   ├── auth.py            # JWT & API key auth
│   │   └── logger.py          # Logging config
│   │
│   ├── db/
│   │   └── database.py        # Async database session
│   │
│   ├── v1/
│   │   ├── models/            # SQLModel ORM models
│   │   │   ├── user.py
│   │   │   ├── wallet.py
│   │   │   └── api_key.py
│   │   │
│   │   ├── routes/            # API endpoints
│   │   │   ├── auth.py
│   │   │   ├── wallet.py
│   │   │   └── keys.py
│   │   │
│   │   ├── services/          # Business logic
│   │   │   ├── auth.py
│   │   │   ├── wallet.py
│   │   │   ├── keys.py
│   │   │   └── paystack.py
│   │   │
│   │   └── schemas/           # Pydantic schemas
│   │       ├── response.py
│   │       └── wallet.py
│   │
│   └── utils/
│       ├── exceptions.py      # Custom exceptions
│       ├── response.py        # Response helpers
│       ├── pagination.py      # Pagination utils
│       └── handlers.py        # Exception handlers
│
└── nginx/
    └── nginx.conf.template    # Nginx reverse proxy config
```

## API Endpoints

### Authentication
- `GET /auth/google` - Start Google OAuth
- `GET /auth/google/callback` - OAuth callback
- `POST /auth/logout` - Logout

### Wallet
- `POST /wallet/deposit` - Initialize deposit (Paystack)
- `GET /wallet/verify/{reference}` - Verify transaction
- `GET /wallet/balance` - Get balance
- `POST /wallet/transfer` - Transfer to another wallet
- `GET /wallet/transactions?page=1&page_size=20` - Transaction history (paginated)
- `POST /wallet/paystack/webhook` - Paystack webhook handler

### API Keys
- `POST /keys` - Create API key
- `GET /keys` - List all keys
- `GET /keys/{key_id}` - Get specific key
- `POST /keys/{key_id}/rollover` - Rollover expired key
- `POST /keys/{key_id}/revoke` - Revoke key
- `DELETE /keys/{key_id}` - Delete key

### Health
- `GET /health` - Health check

## Environment Setup

Create `.env` file with required variables:

```bash
# App
DEBUG=True
ENVIRONMENT=development
APP_PORT=8000

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
DB_USER=wallet_user
DB_PASS=wallet_password
DB_NAME=wallet_db
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Authentication
JWT_SECRET=your-secret-key-here
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Paystack
PAYSTACK_SECRET_KEY=sk_test_xxx
PAYSTACK_PUBLIC_KEY=pk_test_xxx
PAYSTACK_WEBHOOK_SECRET=your-webhook-secret

# API Keys
API_KEY_MAX_PER_USER=5
```

## Running the Application

### With Docker (Recommended)

```bash
docker-compose up --build

# Access at:
# - API via Nginx: http://localhost
# - API Docs: http://localhost/docs
# - Direct API: http://localhost:8000
```

### Manual Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app
```

## Docker Services

The application runs with 4 containers:

1. **PostgreSQL** - Database (port 5432)
2. **Redis** - Cache (port 6379)
3. **API** - FastAPI application (port 8000)
4. **Nginx** - Reverse proxy (port 80)

## Authentication

**JWT (User Authentication)**
```
Authorization: Bearer <jwt_token>
```

**API Key (Service-to-Service)**
```
x-api-key: sk_live_xxxxx
```

## Features

### Authentication & Authorization
- **Google OAuth 2.0** - Secure user authentication with JWT tokens
- **API Key Management** - Service-to-service authentication with granular permissions
- **Permission-based Access Control** - Fine-grained permissions (deposit, transfer, read) on API keys
- **Automatic Wallet Creation** - Wallets created on first user login

### Payment & Transactions
- **Paystack Integration** - Secure payment processing for deposits
- **Webhook Verification** - HMAC-SHA512 signature validation for webhook security
- **Transaction Verification** - Check transaction status via Paystack API or local database
- **Idempotency** - Duplicate transaction prevention using unique references
- **ACID Compliance** - Atomic wallet operations ensuring data consistency
- **Transfer System** - Wallet-to-wallet transfers with balance validation

### Data & Performance
- **Pagination** - Efficient transaction history with configurable page sizes (max 100 per page)
- **Async Operations** - Non-blocking database queries with SQLAlchemy async
- **Connection Pooling** - Optimized database connections
- **Redis Caching** - Ready for session and cache management

### Security
- **API Key Limits** - Maximum 5 active keys per user
- **Key Expiration** - Time-based API key expiration with rollover support
- **Key Revocation** - Instant API key revocation
- **Webhook Signatures** - Cryptographic verification of payment webhooks
- **Environment-based Secrets** - All sensitive data in environment variables

### Developer Experience
- **Standardized Responses** - Consistent JSON response format across all endpoints
- **Auto-generated Docs** - Interactive Swagger UI at `/docs`
- **Comprehensive Logging** - Request/response logging with file rotation
- **Error Handling** - User-friendly error messages with detailed error codes
- **Docker Support** - Full containerization with Nginx reverse proxy

## Response Format

**Success**
```json
{
  "status_code": 200,
  "success": true,
  "message": "Operation successful",
  "data": {...}
}
```

**Error**
```json
{
  "status_code": 400,
  "success": false,
  "message": "Error message",
  "detail": "ERROR_CODE"
}
```

## Development

```bash
# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Rebuild after changes
docker-compose up --build
```
