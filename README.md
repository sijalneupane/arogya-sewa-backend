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