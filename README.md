# FastAPI Base

Base repo backend cho FastAPI: async SQLAlchemy 2.0, Alembic, JWT auth, error shape thống nhất, test sẵn chạy.

## Stack

| Thành phần | Lựa chọn | Ghi chú |
|---|---|---|
| Framework | FastAPI + Uvicorn | app factory trong `app/main.py` |
| Validation / Settings | Pydantic v2 + pydantic-settings | settings đọc `.env` một lần, có cache |
| ORM | SQLAlchemy 2.0 (async, `Mapped[]`) | Postgres qua `asyncpg`, SQLite qua `aiosqlite` |
| Migration | Alembic (async env) | `migrations/` |
| Auth | JWT (PyJWT) + bcrypt | access token + refresh token |
| Test | pytest + pytest-asyncio + httpx | SQLite in-memory, không cần DB thật |
| Lint | ruff + mypy | `make lint` |

## Chạy nhanh

```bash
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Muốn chạy ngay không cần Postgres: sửa .env
# DATABASE_URL=sqlite+aiosqlite:///./app.db

alembic revision --autogenerate -m "init"   # tạo migration đầu tiên
alembic upgrade head
uvicorn app.main:app --reload
```

Mở http://localhost:8000/docs

Hoặc dùng Docker (kèm Postgres, tự chạy migration):

```bash
cp .env.example .env
docker compose up --build
```

Test:

```bash
pytest -q          # 9 test sẵn có: health, register/login/refresh/me, phân quyền, error shape
```

## Cấu trúc

```
app/
├── main.py                  # create_app(): middleware, exception handler, include router, lifespan
├── core/
│   ├── config.py            # Settings (env) - nguồn sự thật duy nhất về config
│   ├── security.py          # hash/verify password, create/decode JWT
│   ├── exceptions.py        # AppError + handler → format lỗi thống nhất
│   └── logging.py           # setup logging
├── db/
│   ├── base.py              # DeclarativeBase + mixin (UUID id, created_at/updated_at)
│   └── session.py           # engine, session factory, dependency get_db
├── models/                  # SQLAlchemy models (tầng DB)
├── schemas/                 # Pydantic models (tầng I/O - request/response)
├── services/                # business logic, nhận AsyncSession qua constructor
└── api/
    ├── deps.py              # dependencies dùng lại: get_db, get_current_user, get_current_superuser
    └── v1/
        ├── router.py        # gom router của v1
        └── endpoints/       # health.py, auth.py, users.py - chỉ điều phối, không chứa logic
migrations/                  # Alembic (env.py đã cấu hình async + đọc DATABASE_URL từ settings)
tests/
```

Quy ước quan trọng: **endpoint mỏng, service chứa logic, model ≠ schema.** Endpoint chỉ nhận request, gọi service, trả schema. Không import model trực tiếp vào response.

### Đối chiếu với NestJS

| NestJS | Ở đây |
|---|---|
| `@Module` | package trong `app/` + đăng ký router ở `api/v1/router.py` |
| `@Controller` | file trong `api/v1/endpoints/` |
| `@Injectable()` service | class trong `services/`, inject qua `Depends` |
| `ConfigModule` | `core/config.py` |
| DTO + `class-validator` | Pydantic schema trong `schemas/` |
| Guard (`AuthGuard`) | dependency `get_current_user` / `get_current_superuser` |
| `ExceptionFilter` | `core/exceptions.py` |
| TypeORM migration | Alembic |

## API có sẵn

| Method | Path | Auth |
|---|---|---|
| GET | `/api/v1/health` | – |
| GET | `/api/v1/health/db` | – |
| POST | `/api/v1/auth/register` | – |
| POST | `/api/v1/auth/login` | – |
| POST | `/api/v1/auth/refresh` | refresh token |
| GET | `/api/v1/auth/me` | access token |
| GET | `/api/v1/users` | superuser (có phân trang) |
| GET | `/api/v1/users/{id}` | access token |
| PATCH | `/api/v1/users/{id}` | superuser |
| DELETE | `/api/v1/users/{id}` | superuser |

Mọi lỗi trả về cùng một shape, FE parse một chỗ là xong:

```json
{ "error": { "code": "conflict", "message": "Email already registered" } }
```

`422` có thêm `error.details` là danh sách lỗi field của Pydantic.

## Thêm một resource mới (ví dụ `posts`)

1. `app/models/post.py` → khai báo model, rồi export trong `app/models/__init__.py` (Alembic autogenerate chỉ thấy model đã được import).
2. `app/schemas/post.py` → `PostCreate`, `PostUpdate`, `PostRead`.
3. `app/services/post_service.py` → logic, nhận `AsyncSession`.
4. `app/api/v1/endpoints/posts.py` → router mỏng, dùng `CurrentUser` nếu cần auth.
5. Đăng ký vào `app/api/v1/router.py`.
6. `alembic revision --autogenerate -m "add posts"` → đọc lại file sinh ra → `alembic upgrade head`.

## Lưu ý trước khi lên production

- `SECRET_KEY`: sinh bằng `openssl rand -hex 32`, không commit.
- `ENVIRONMENT=production` sẽ tự tắt `/docs` và `/openapi.json`.
- `DATABASE_URL` phải dùng driver async (`postgresql+asyncpg://`), không phải `psycopg2`.
- Đã có `pool_pre_ping=True`; cân nhắc thêm `pool_size` / `max_overflow` theo tải.
- Chưa có: rate limit, refresh-token revocation (lưu jti vào Redis/DB), email verify, RBAC chi tiết, CI. Thêm khi thực sự cần.
