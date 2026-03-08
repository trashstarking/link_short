Попытка в сервис для сокращения длинных ссылок.
Позволяет создавать короткие ссылки, отслеживать статистику переходов и управлять ими через личный кабинет.

**Демо сервиса:** https://home-shortener.onrender.com/
**Документация API (Swagger):** `/docs`

## Функционал

### Обязательные функции:
1.  **Сокращение ссылок**: `POST /links/shorten` (автоматическая генерация или кастомный alias).
2.  **Редирект**: `GET /{short_code}` (моментальное перенаправление на оригинал).
3.  **Управление**: Удаление `DELETE` и изменение `PUT` ссылок (только для владельца).
4.  **Статистика**: `GET /links/{short_code}/stats` (количество кликов, дата создания).
5.  **Поиск**: Поиск короткой ссылки по оригинальному URL.
6.  **Время жизни**: Возможность задать `expires_at` (ссылка удалится автоматически).

### Дополнительные функции:
1.  **Кэширование**: Горячие ссылки кэшируются в Redis для ускорения ответа.
2.  **Фоновые задачи**: Background Task автоматически очищает просроченные ссылки раз в минуту.
3.  **История**: Просмотр истории истекших ссылок.
4.  **Frontend**: Полноценный веб-интерфейс с регистрацией и дашбордом.

## Инструкция по запуску (Локально)

Для запуска требуется установленный **Docker** и **Docker Compose**.

1. **Клонировать репозиторий:**
   ```bash
   git clone https://github.com/trashstarking/link_short.git
   cd url_shortener
   ```

2. **Создать файл .env:**
   В корне проекта создайте файл `.env`:
   ```env
   DATABASE_URL=postgresql://postgres:postgres@db:5432/shortener_db
   REDIS_URL=redis://redis:6379/0
   SECRET_KEY=super_secret_key_change_me
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

3. **Запустить контейнеры:**
   ```bash
   docker-compose up --build
   ```

4. **Открыть в браузере:**
   - Главная страница: [http://localhost:8000]
   - Swagger UI: [http://localhost:8000/docs]

---

## Описание API и примеры запросов

### 1. Регистрация пользователя
**POST** `/register`
```json
{
  "username": "user1",
  "password": "password123"
}
```

### 2. Создание короткой ссылки
**POST** `/links/shorten`
*(Требуется Header: Authorization: Bearer <token> для привязки к аккаунту)*
```json
{
  "original_url": "https://google.com",
  "custom_alias": "my-google",
  "expires_at": "2025-01-01T12:00:00"
}
```

### 3. Получение статистики
**GET** `/links/{short_code}/stats`
**Ответ:**
```json
{
  "short_code": "my-google",
  "original_url": "https://google.com",
  "click_count": 42,
  "is_active": true
}
```

## Структура Базы Данных (PostgreSQL)

### Таблица `users`
- `id`: Primary Key
- `username`: Уникальное имя
- `hashed_password`: Хеш пароля

### Таблица `links`
- `id`: Primary Key
- `original_url`: Целевая ссылка
- `short_code`: Уникальный код (индекс)
- `click_count`: Счётчик переходов
- `created_at`: Дата создания
- `expires_at`: Дата истечения (Null если вечная)
- `is_active`: Статус (Soft Delete)
- `user_id`: Foreign Key на `users`
```
