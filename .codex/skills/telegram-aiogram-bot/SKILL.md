# Telegram aiogram bot skill

Use this skill when working on Telegram bot features.

Project structure:
- bot/
  - handlers/
  - keyboards/
  - services/
  - repositories/
  - database/
  - states/
  - middlewares/

When adding a feature:
1. Add or update handler
2. Add service logic
3. Add repository method if DB is needed
4. Add keyboard if needed
5. Update texts/constants
6. Add tests if possible

Rules:
- aiogram 3 syntax only
- async SQLAlchemy only
- no token in code
- no business logic inside handlers