from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from app.core.config import Settings


class IsSuperAdmin(BaseFilter):
    def __init__(self, settings: Settings) -> None:
        self._ids = set(settings.super_admin_id_list)

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return bool(user and user.id in self._ids)
