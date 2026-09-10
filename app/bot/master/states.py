from aiogram.fsm.state import State, StatesGroup


class AddBotStates(StatesGroup):
    waiting_for_token = State()


class SetGroupStates(StatesGroup):
    waiting_for_group_id = State()


class EditLocaleStates(StatesGroup):
    waiting_for_locale_key = State()
    waiting_for_locale_value = State()
