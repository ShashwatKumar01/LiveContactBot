from aiogram.fsm.state import State, StatesGroup


class AddBotStates(StatesGroup):
    waiting_for_token = State()


class SetGroupStates(StatesGroup):
    waiting_for_group_id = State()


class EditBotTextStates(StatesGroup):
    waiting_for_value = State()


class BroadcastStates(StatesGroup):
    composing = State()
