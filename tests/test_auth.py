from httpx import AsyncClient


async def test_register_then_login_and_me(client: AsyncClient, user_payload: dict) -> None:
    res = await client.post("/auth/register", json=user_payload)
    assert res.status_code == 201, res.text
    assert res.json()["email"] == user_payload["email"]
    assert "password" not in res.json()

    res = await client.post(
        "/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )
    assert res.status_code == 200
    tokens = res.json()

    res = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert res.status_code == 200
    assert res.json()["full_name"] == "Khoa"


async def test_duplicate_email_conflicts(client: AsyncClient, user_payload: dict) -> None:
    assert (await client.post("/auth/register", json=user_payload)).status_code == 201
    res = await client.post("/auth/register", json=user_payload)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "conflict"


async def test_login_with_wrong_password(client: AsyncClient, user_payload: dict) -> None:
    await client.post("/auth/register", json=user_payload)
    res = await client.post(
        "/auth/login", json={"email": user_payload["email"], "password": "wrong-password"}
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "unauthorized"


async def test_me_requires_token(client: AsyncClient) -> None:
    assert (await client.get("/auth/me")).status_code == 401


async def test_refresh_token_flow(client: AsyncClient, user_payload: dict) -> None:
    await client.post("/auth/register", json=user_payload)
    login = await client.post(
        "/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )
    refresh_token = login.json()["refresh_token"]

    res = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    assert res.json()["access_token"]

    # An access token must not be accepted where a refresh token is required.
    res = await client.post("/auth/refresh", json={"refresh_token": login.json()["access_token"]})
    assert res.status_code == 401


async def test_validation_error_shape(client: AsyncClient) -> None:
    res = await client.post("/auth/register", json={"email": "not-an-email", "password": "short"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"


async def test_users_list_requires_superuser(client: AsyncClient, user_payload: dict) -> None:
    await client.post("/auth/register", json=user_payload)
    login = await client.post(
        "/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )
    token = login.json()["access_token"]
    res = await client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
