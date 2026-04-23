from typing import List
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document
from app.utils.html_cleaner import HTMLCleaner

class CustomHTMLLoader(BaseLoader):
    def __init__(self, file_path: str, meta_type: str, selector: dict = None):
        self.file_path = file_path
        self.meta_type = meta_type
        self.selector = selector

    async def load(self) -> List[Document]:
        return await HTMLCleaner.process(path=self.file_path, meta_type=self.meta_type, selector=self.selector)