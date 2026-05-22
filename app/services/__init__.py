from app.services.admin_service import is_admin
from app.services.stats_service import StatsService
from app.services.topic_service import TopicService
from app.services.training_service import TrainingService
from app.services.user_service import UserService
from app.services.word_service import WordService

__all__ = ["is_admin", "UserService", "TrainingService", "TopicService", "StatsService", "WordService"]
