from typing import List, Dict, Any

from app.ports import CategoryRepositoryPort
from database.repositories.category_repository import CategoryRepository


class CategoryService:
    def __init__(self, category_repository: CategoryRepositoryPort | None = None):
        self.category_repository = category_repository or CategoryRepository()

    def list_categories(self) -> List[Dict[str, Any]]:
        return self.category_repository.list_categories()
