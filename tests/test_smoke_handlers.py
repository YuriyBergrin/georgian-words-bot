import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.handlers import admin_manage, admin_words_search, training


class SmokeHandlersTest(unittest.IsolatedAsyncioTestCase):
    async def test_add_admin_handler_uses_services_di(self) -> None:
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=100),
            answer=AsyncMock(),
        )
        services = SimpleNamespace(
            admin_manage=SimpleNamespace(
                is_bootstrap_admin=lambda _: True,
                add_admin=AsyncMock(return_value=True),
            )
        )
        command = SimpleNamespace(args="123")

        await admin_manage.add_admin_handler(message, command, services)

        services.admin_manage.add_admin.assert_awaited_once_with(123)
        message.answer.assert_awaited_once()

    async def test_search_edit_uses_selected_row_without_retyping(self) -> None:
        message = SimpleNamespace(answer=AsyncMock())
        state = SimpleNamespace(get_data=AsyncMock(return_value={"search_rows": ["ქოთანი"]}))
        services = SimpleNamespace()

        with patch("app.handlers.admin_words_search.start_edit_word_flow", new=AsyncMock()) as start_flow:
            await admin_words_search.edit_word_from_search_handler(message, state, services)
            start_flow.assert_awaited_once_with(message, state, "ქოთანი", services)

    async def test_training_all_words_mode_uses_services_di(self) -> None:
        message = SimpleNamespace(from_user=SimpleNamespace(id=1))
        state = SimpleNamespace(update_data=AsyncMock())
        services = SimpleNamespace(training_flow=SimpleNamespace())

        with patch("app.handlers.training.send_random_word", new=AsyncMock()) as send_random_word:
            await training.learn_all_words_mode_handler(message, state, services)
            state.update_data.assert_awaited_once_with(selected_topic=None)
            send_random_word.assert_awaited_once_with(message, state, services)


if __name__ == "__main__":
    unittest.main()
