import os
import time
import httpx
from charset_normalizer import from_bytes
from loguru import logger

class HTTPDownloader():

    def __init__(self, url: str, file_path: str, cache_hours: int = 24):
        self.url = url
        self.file_path = file_path
        self.cache_hours = cache_hours
        

    async def run(self) -> str:
        #print(f"Проверяем необходимость обновления кэша для {self.file_path}...")
        if not self._should_update():
            logger.info(f"Используем кэш источника {self.url}")
            return
        logger.info(f"Обновляем кэш источника {self.url}")
        await self.download_and_save()


    def _should_update(self) -> bool:
        if not os.path.exists(self.file_path):
            return True
        if self.cache_hours == 0:
            return False
        
        file_age = time.time() - os.path.getmtime(self.file_path)
        return file_age > (self.cache_hours * 3600)


    async def download_and_save(self):
        downloaded_content = await self._download()
        if downloaded_content:
            await self._write_cache(downloaded_content)
        
    async def _download(self) -> str:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            async with httpx.AsyncClient(follow_redirects=True, timeout=20.0, headers=headers) as client:
                response = await client.get(self.url)
                response.raise_for_status()
                
                # Используем байты, так как response.text может ошибиться с кодировкой
                raw_bytes = response.content
                
                # Умное определение кодировки по содержимому
                # charset-normalizer найдет лучшую кодировку (cp1251, utf-8, latin-1 и т.д.)
                result = from_bytes(raw_bytes).best()
                
                if result:
                    #print(f"Определена кодировка: {result.encoding} для {self.url}")
                    return str(result) # Возвращает текст в unicode (utf-8)
                else:
                    # Если не удалось определить, пробуем стандартный метод httpx
                    return response.text
                    
        except Exception as e:
            logger.warning(f"Ошибка при скачивании {self.url}: {e}")
            return None

    async def _write_cache(self, content: str):
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            # Теперь записываем ЛЮБОЙ файл как utf-8
            with open(self.file_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(content)
        except Exception as e:
            logger.warning(f"Ошибка записи кэша {self.file_path}: {e}")