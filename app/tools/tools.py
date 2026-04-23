import httpx
from langchain_core.tools import tool
from loguru import logger

@tool
async def get_order_info(email: str|None=None) -> str:
    """Информация о существующих заказах клиента по email, указанному при оформлении заказа. Если email не указан, то запросить его у пользователя."""

    if not email:
        return "Для получения информации о заказе мне нужен email указанный при оформлении заказа"
    
    url = "https://miniliner.ru/bot/orders.php"
    payload = {
        "email": email,
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json().get('orders', {})
            if data:
                return data
            else:
                return f"Заказы для {email} не найдены."
        except Exception as e:
            print(f"Ошибка: {e}")
    
    return f"Не удалось получить информацию о заказеах для {email}."


@tool
async def get_price(articul: str) -> str:
    """Используй для получения цены товара. 
    ВАЖНО: Ищи артикул (цифровой код) в истории переписки. 
    Если пользователь ранее уже называл артикул, используй его автоматически."""

    url = "https://miniliner.ru/bot/stocks_n_prices.php"
    payload = {
        "articuls": [articul]
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            if 'stocks' in data and data['stocks']:
                return f"Товар с артикулом {articul} стоит {data['stocks'][0]['price']} руб."               
            return f"Товар с артикулом {articul} не найден."    
        
        except ValueError as e:
            print(f"Ой, ошибка: {e}")

@tool
async def get_stocks(articul: str) -> str:
    """Используй для получения количества товара на складе. 
    ВАЖНО: Ищи артикул в истории переписки. 
    Если пользователь ранее уже называл артикул, используй его автоматически."""

    url = "https://miniliner.ru/bot/stocks_n_prices.php"
    payload = {
        "articuls": [articul]
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            if 'stocks' in data and data['stocks']:
                return f" Количество товара с артикулом {articul}: {data['stocks'][0]['stock']} шт."               
            return f"Товар с артикулом {articul} не найден."    
        
        except ValueError as e:
            print(f"Ой, ошибка: {e}")


@tool
async def make_order_link(articul: str, military: bool) -> str:
    """Генерирует ссылку на оформление заказа выбранного товара. Используй когда клиент явно спрашивает как купить или заказать товар. 
    В зависимости от каталога военных или гражданских моделей, нужно указывать флаг military."""

    if not articul:
        return "Для оформления заказа мне нужны артикул товара."
    domen = "aviadivision.ru" if military else "miniliner.ru"
    link = f"https://{domen}/personal/basket/?articul={articul}"

    return f"Товар уже в корзине, осталось перейти по ссылке {link} и оформить заказ."


@tool
async def delivery_cost(city: str, index: str) -> str:
    """Рассчитывет примерную стоимость доставки службой СДЭК и Почтой России до указанного города или страны.
    Нужно указать название города или страны для СДЭК, и индекс для Почты России.
    Используй если клиент интересуется стоимостью доставки."""

    if not city:
        return "Для оформления заказа мне нужно название города."
    
    url = "https://miniliner.ru/bot/delivery_cost.php"

    result = []
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json={"city": city})
            response.raise_for_status()
            data = response.json()

            if 'SDEK' in data:
                result.append(f"До пункта выдачи СДЭК: {data['SDEK']['cost']} руб. Срок: {data['SDEK']['period']} дней.")
            if 'SDEK_CURIER' in data:
                result.append(f"Курьером СДЭК: {data['SDEK_CURIER']['cost']} руб.Срок: {data['SDEK_CURIER']['period']} дней.")

            response = await client.post(url, json={"index": index})
            response.raise_for_status()
            data = response.json()

            if 'POCHTA' in data:
                result.append(f"Почта России: {data['POCHTA']['cost']} руб. Срок: {data['POCHTA']['period']} дней.")
            
        except ValueError as e:
            print(f"Ой, ошибка: {e}")

    
    if result: 
        return "Ориентировочные цены:\n" + "\n".join(result)
   
    return f"Не удалось рассчитать доставку до {city}."



@tool
async def get_product_info(articul: str) -> str:
    """Используй для получения дополнительных фотографий. 
    ВАЖНО: Ищи артикул товара в истории переписки. 
    Если пользователь ранее уже называл артикул, используй его автоматически."""

    url = "https://miniliner.ru/bot/product_info.php"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json={"articul": articul})
            #response.raise_for_status()
            data = response.json()
            if 'offer' in data and data['offer']:
                offer = data['offer']
                offer_str =  f"""Модель: {offer.get('name')}, производитель: {offer.get('vendor', 'не указан')}, цена: {offer.get('price', 'не указано')}, артикул: {offer.get('articul', 'не указан')}, масштаб: {offer.get('scale', 'не указан')},ссылка: {offer.get('link', 'нет')}"""
                if 'images' in offer and offer['images']:
                    offer_str += f"\nФото: {', '.join(offer['images'])}"
                return offer_str
               
        except ValueError as e:
            logger.warning(f"Ой, ошибка: {e}")
            

    return f"Новинки не найдены."  


@tool
async def get_new_products() -> str:
    """Используй для получения информации о новинках в магазине."""
    return await get_products(type="new")

@tool
async def get_discount_products() -> str:
    """Используй для получения информации о распродажах и скидках в магазине."""
    return await get_products(type="discount")

@tool
async def get_soon_products() -> str:
    """Используй для получения информации о товарах которые скоро поступят в продажу."""
    return await get_products(type="soon")

@tool
async def get_populars_products() -> str:
    """Используй для рекомендации товаров клиенту."""
    return await get_products(type="popular")

async def get_products(type: str) -> str:
    url = "https://miniliner.ru/bot/product_list.php"

    async with httpx.AsyncClient() as client:
        try:
            offers = []
            response = await client.post(url, json={"type": type})
            response.raise_for_status()
            data = response.json()

            if 'offers' in data:
                for offer in data['offers'].values():
                    #print(offer.get('name') + "+")
                    price = offer.get('price', offer.get('discount_price', 'не указано'))
                    offers.append(f"""Модель: {offer.get('name')}, производитель: {offer.get('vendor', 'не указан')}, цена: {price}, артикул: {offer.get('articul', 'не указан')}, масштаб: {offer.get('scale', 'не указан')},ссылка: {offer.get('link', 'нет')}, фото: {offer.get('image', 'нет')}""")      
            if offers:
                print(offers)
                return "\n".join(offers)
               
        except ValueError as e:
            print(f"Ой, ошибка: {e}")

    return f"Новинки не найдены."  



# Список всех инструментов для привязки к модели
ALL_TOOLS = [
    get_price,
    get_stocks,
    delivery_cost, 
    get_order_info,
    get_product_info,
    get_new_products,
    get_soon_products,
    get_populars_products,
    get_discount_products
]
# Мапа для быстрого вызова по имени
TOOLS_MAP = {t.name: t for t in ALL_TOOLS}