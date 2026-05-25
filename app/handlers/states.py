from aiogram.fsm.state import State, StatesGroup


class AddWordForm(StatesGroup):
    georgian = State()
    russian = State()
    topic = State()
    topic_custom = State()


class LearnWordForm(StatesGroup):
    mode = State()
    topic = State()
    answer = State()


class BulkImportForm(StatesGroup):
    mode = State()
    payload = State()


class EditWordForm(StatesGroup):
    georgian = State()
    russian = State()
    topic = State()


class SearchWordForm(StatesGroup):
    query = State()
    browse = State()


class DeleteWordForm(StatesGroup):
    georgian = State()


class BrowseTopicsForm(StatesGroup):
    topic = State()
    delete_topic = State()
    delete_topic_confirm = State()
