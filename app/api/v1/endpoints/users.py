import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentSuperuser, CurrentUser, UserServiceDep
from app.schemas.common import Page, PageParams
from app.schemas.user import UserRead, UserUpdate

router = APIRouter()


@router.get("", response_model=Page[UserRead])
async def list_users(
    users: UserServiceDep,
    _: CurrentSuperuser,
    params: Annotated[PageParams, Depends()],
) -> Page[UserRead]:
    items, total = await users.list_users(offset=params.offset, limit=params.size)
    return Page[UserRead](
        items=[UserRead.model_validate(u) for u in items],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: uuid.UUID, users: UserServiceDep, _: CurrentUser) -> UserRead:
    return UserRead.model_validate(await users.get_by_id(user_id))


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    users: UserServiceDep,
    _: CurrentSuperuser,
) -> UserRead:
    return UserRead.model_validate(await users.update(user_id, payload))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, users: UserServiceDep, _: CurrentSuperuser) -> None:
    await users.delete(user_id)
