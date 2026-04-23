import asyncio
import json
from langchain_core.documents import Document
from bs4 import BeautifulSoup
import aiofiles

class HTMLCleaner:
    @staticmethod
    async def process(path: str, meta_type: str, selector: dict = None) -> list[Document]:
        """Извлекает очищенный текст из HTML по заданному селектору."""
        async with aiofiles.open(path, mode='r', encoding='utf-8') as f:
            html_content = await f.read()

        metadata = {"source": path, "type": meta_type}

        def _extract():
            docs = []

            soup = BeautifulSoup(html_content, 'lxml')
            title_text = soup.title.string if soup.title else None
            canonical_tag = soup.find('link', rel='canonical')
            if canonical_tag:
                metadata["link"] = canonical_tag.get('href')

            
            #schema.org meta
            schema_script = soup.find('script', type='application/ld+json')
            if schema_script:
                # Загружаем json
                schema_data = json.loads(schema_script.string)
                
                # Обработка случая, если это список схем
                if isinstance(schema_data, list):
                    data = schema_data[0]
                else:
                    data = schema_data
                    
                # Извлекаем name и description
                metadata["title"] = data.get("name", title_text)
                metadata["description"] = data.get("description")
                metadata["type"] = data.get("@type", metadata["type"])
                


            # Поиск целевого узла
            if selector:
                # Распаковываем словарь (например, {'class_': 'main'}) в аргументы find()
                target_node = soup.find(**selector)
                if not target_node:
                    #print(f"[Warning] Селектор {selector} не найден в {path}. Используем body.")
                    target_node = soup.find('body')
            else:
                target_node = soup.find('body')

            if not target_node:
                return ""

            # Удаляем лишние теги, которые портят эмбеддинги
            for trash in target_node(["script", "style", "form", "iframe", "nav", "footer", "header"]):
                trash.extract()

            links = []
            for a in target_node.find_all('a', href=True):
                links.append(a.get('href'))
                #a.string = new_string
            if links:
                metadata["links"] = links

            '''for p in target_node.find_all('p'):
                content = p.get_text(separator="\n", strip=True)
                if content:
                    docs.append(Document(page_content=content, metadata=metadata))
            return docs'''

            result = target_node.get_text(separator="\n", strip=True)
            #print(result)
            return Document(page_content=result, metadata=metadata)

        documents = await asyncio.get_event_loop().run_in_executor(None, _extract)
        
        return [documents]
        
        '''return Document(
            page_content=clean_text, 
            #metadata={"source": path, "type": meta_type}
            metadata=metadata
        )'''
    

class HTML_Cleaner:
    @staticmethod
    async def process(html_content: str, selector: dict = None) -> Document:
        """Извлекает очищенный текст из HTML по заданному селектору."""

        def _extract():
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Поиск целевого узла
            if selector:
                # Распаковываем словарь (например, {'class_': 'main'}) в аргументы find()
                target_node = soup.find(**selector)
                if not target_node:
                    print(f"[Warning] Селектор {selector} не найден. Используем body.")
                    target_node = soup.find('body')
            else:
                target_node = soup.find('body')

            if not target_node:
                return ""

            # Удаляем лишние теги, которые портят эмбеддинги
            for trash in target_node(["script", "style", "nav", "footer", "header"]):
                trash.extract()

            # Получаем текст, разделяя блоки переносом строки для лучшего сплиттинга
            return target_node.get_text(separator="\n", strip=True)

        clean_text = await asyncio.get_event_loop().run_in_executor(None, _extract)
        print(clean_text)

        return clean_text