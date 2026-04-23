from typing import List
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    JSONLoader
)
from langchain_community.document_loaders.base import BaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app import CLIENT_CACHE_DIR
from app.RAG.custom_html_loader import CustomHTMLLoader
from app.RAG.custom_xml_loader import CustomXMLLoader
from app.utils.common import get_file_type, get_rag_cache_path


class DocumentProcessor:
    def __init__(self, source: dict):
        self.loaders = {
            "application/pdf": PyPDFLoader,
            "application/msword": Docx2txtLoader,
            "application/msword": Docx2txtLoader,
            "text/plain": TextLoader,
            "application/json": JSONLoader,
            "text/xml": CustomXMLLoader,
            "text/html": CustomHTMLLoader,
        }
        self.file_config = source

        self.meta_type = self.file_config.get("meta_type", "general_info")  
        self.meta_sub_type = self.file_config.get("meta_sub_type", None) 
        self.file_path = get_rag_cache_path(source=self.file_config, cache_dir=CLIENT_CACHE_DIR)    
        self.file_type = get_file_type(self.file_path)

        
    async def load_file(self):
        if self.file_type not in self.loaders:
            print(f"Формат {self.file_type} не поддерживается для файла: {self.file_path}")
            return []

        loader_class = self.loaders[self.file_type]

        awaitable = False
        
        # Особенности для JSON (нужно указать jq_schema для извлечения текста)
        if self.file_type == "application/json":
            loader = loader_class(self.file_path, jq_schema=".[]", text_content=False)
        elif self.file_type in ["text/xml", "application/xml"]:
            awaitable = True
            item_tag = self.file_config["settings"].get("item_tag", "offer1")
            loader = loader_class(
                file_path=self.file_path, meta_type=self.meta_type, item_tag=item_tag)
        elif self.file_type in ["text/html"]:
            awaitable = True
            selector = self.file_config["settings"].get("selector", 'body')
            loader = loader_class(
                file_path=self.file_path, meta_type=self.meta_type, selector=selector)
        else:
            loader = loader_class(self.file_path)

        if awaitable:
            documents = await loader.load()  
        else:
            documents = loader.load()
        
        for doc in documents: 
            doc.metadata["source"] = self.file_config.get("url", "")
            doc.metadata["type"] = self.meta_type
            doc.metadata["sub_type"] = self.meta_sub_type


        return documents

    
    async def process_document(self, chunk_size=1000, chunk_overlap=200):
        print(f"Загрузка: {self.file_path}")
        all_docs = []
        all_docs.extend(await self.load_file())

        # Разбиение на чанки
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap
        )
        return splitter.split_documents(all_docs)