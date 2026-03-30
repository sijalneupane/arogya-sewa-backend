# My FastAPI Project

> A clean, production-ready FastAPI template with **SQLAlchemy** + **Pydantic v2**.

## Folder overview
| Folder      | Purpose |
|-------------|---------|
| `app/`      | Main folder for application (main, routers, dependencies) |
|`app/api/`|Includes version specific router and dependencies|
| `app/core/`     | Config, security, utilities |
| `app/db/`       | Database session management |
| `app/models/`   | **Database tables** (SQLAlchemy ORM) |
| `app/schemas/`  | **API contracts** (Pydantic request/response models) |
| `app/services/`  | Business logic and service layer |
| `app/utils/`     | Utility functions and helpers |
| `tests/`        | Pytest suite |

---

## Mailgun setup

Set these environment variables before running the API:

```env
MAILGUN_ENABLED=true
MAILGUN_API_KEY=key-xxxxxxxxxxxxxxxxxxxx
MAILGUN_DOMAIN=mg.example.com
MAILGUN_BASE_URL=https://api.mailgun.net/v3
MAILGUN_FROM_EMAIL=Arogya Sewa <no-reply@mg.example.com>
MAILGUN_WEBHOOK_SIGNING_KEY=xxxxxxxxxxxxxxxxxxxx
MAILGUN_TIMEOUT_SECONDS=15
```

For EU domains, use:

```env
MAILGUN_BASE_URL=https://api.eu.mailgun.net/v3
```

### Email routes

The following routes are available under `API_V1_STR`:

- `POST /email/mailgun/webhooks/events`

Webhook endpoint verifies Mailgun HMAC SHA256 signatures using
`MAILGUN_WEBHOOK_SIGNING_KEY` before processing events.