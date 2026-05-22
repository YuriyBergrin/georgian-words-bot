from aiogram.fsm.state import State, StatesGroup


class AddWordForm(StatesGroup):
    georgian = State()
    russian = State()
    topic = State()


class LearnWordForm(StatesGroup):
    mode = State()
    topic = State()
    answer = State()


class BulkImportForm(StatesGroup):
    payload = State()


class EditWordForm(StatesGroup):
    georgian = State()
    russian = State()
    topic = State()

