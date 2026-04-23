import re
import aiofiles
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document
from lxml import etree


class CustomXMLLoader(BaseLoader):
    def __init__(self, file_path: str, meta_type: str, item_tag: str = "offer"):
        self.file_path = file_path
        self.meta_type = meta_type
        self.item_tag = item_tag

    async def load(self):
        documents = []
        
        try:
            # Читаем байты
            async with aiofiles.open(self.file_path, mode='r', encoding='utf-8') as f:
                xml_text = await f.read()
            
            xml_text = re.sub(r'encoding="[^"]+"', 'encoding="utf-8"', xml_text, count=1)
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(xml_text.encode('utf-8'), parser=parser)

            offers = root.xpath(f"//*[local-name()='{self.item_tag}']")

            for offer in offers:
                metadata={"source": self.file_path, "type": self.meta_type}

                id = offer.get('id', None).strip()
                if not id:
                    continue

                model = offer.findtext('model', 'Нет').strip()
                vendor = offer.findtext('vendor', 'Нет').strip()
                description = offer.findtext('description', 'Нет').strip()
                link = offer.findtext('url','').strip()
                image = offer.findtext('picture', 'Нет').strip()
                product_id = offer.get('id', '0')

                if product_id:
                    metadata["id"] = product_id
                if link:
                    metadata["link"] = link
                if image:
                    metadata["image"] = image


                '''document = Document(
                        page_content=f"""Идентификатор товара(id): {offer.get('id', '0')}. Товар: {model}. Производитель: {vendor}. Фотография: {picture}. Описание: {description}. Ссылка: {url}""".strip(),
                        metadata={"source": self.file_path, "type": self.meta_type}
                )'''

                document = Document(
                        page_content=f"""Название: {model}. Производитель: {vendor}. Описание: {description}.""".strip(),
                        metadata=metadata
                )

                documents.append(document)

            return documents

        except Exception as e:
            print(f"Ошибка при разборе: {e}")
            return []