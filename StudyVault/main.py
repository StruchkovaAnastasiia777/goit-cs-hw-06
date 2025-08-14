#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import socket
import threading
import json
import urllib.parse
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pymongo import MongoClient
import os
import mimetypes


class StudyVaultHTTPHandler(BaseHTTPRequestHandler):
    """HTTP сервер для StudyVault з підтримкою існуючого frontend"""

    def do_HEAD(self):
        """Обробка HEAD запитів"""
        self.do_GET()

    def do_GET(self):
        """Обробка GET запитів"""

        # Видаляємо query параметри з шляху
        path = self.path.split('?')[0]

        # маршрутизація
        if path == '/' or path == '/index.html':
            self.serve_file('index.html', 'text/html')

        elif path == '/message.html' or path == '/message':
            self.serve_file('message.html', 'text/html')

        elif self.path == '/style.css' or self.path == '/styles.css':
            self.serve_file('style.css', 'text/css')

        elif self.path == '/script.js':
            self.serve_file('script.js', 'application/javascript')

        elif self.path == '/logo.png':
            self.serve_file('logo.png', 'image/png')

        # обробка файлів зі static папки
        elif self.path.startswith('/static/'):
            filename = self.path[8:]  # Видаляємо '/static/'
            if filename == 'script.js':
                self.serve_file('script.js', 'application/javascript')
            elif filename == 'style.css':
                self.serve_file('style.css', 'text/css')
            elif filename == 'logo.png':
                self.serve_file('logo.png', 'image/png')
            else:
                self.serve_static_file(filename)

        elif self.path.startswith('/templates/'):
            filename = self.path[11:]  # Видаляємо '/templates/'
            if filename.endswith('.html'):
                self.serve_file(filename, 'text/html')
            else:
                self.serve_file('error.html', 'text/html', 404)

        else:
            # 404 - повертаємо error.html
            self.serve_file('error.html', 'text/html', 404)

    def do_POST(self):
        """Обробка POST запитів (форма повідомлень)"""

        if self.path == '/message' or self.path == '/send_message':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')

            # Парсинг даних форми
            form_data = urllib.parse.parse_qs(post_data)

            username = form_data.get('username', [''])[0]
            message = form_data.get('message', [''])[0]

            if username and message:
                # відправляє дані на Socket-сервер
                self.send_to_socket_server(username, message)

                # реренаправляє назад з повідомленням про успіх
                self.send_response(302)
                self.send_header('Location', '/message.html?success=1')
                self.end_headers()
            else:
                # Помилка валідації
                self.send_response(302)
                self.send_header('Location', '/message.html?error=1')
                self.end_headers()
        else:
            self.serve_file('error.html', 'text/html', 404)

    def serve_file(self, filename, content_type, status_code=200):
        """Відправка файлу клієнту"""
        # Пошук файлу в різних папках
        search_paths = [
            filename,  # корінь
            f'templates/{filename}',  # templates
            f'static/{filename}'  # static
        ]

        file_found = None
        for path in search_paths:
            if os.path.exists(path):
                file_found = path
                break

        if not file_found:
            self.send_error(404, f"File {filename} not found")
            return

        try:
            with open(file_found, 'rb') as f:
                content = f.read()

            self.send_response(status_code)
            self.send_header('Content-Type', content_type + '; charset=utf-8')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)

        except FileNotFoundError:
            self.send_error(404, f"File {filename} not found")

    def serve_static_file(self, filename):
        """Обробка статичних файлів"""
        try:
            content_type, _ = mimetypes.guess_type(filename)
            if content_type is None:
                content_type = 'application/octet-stream'

            with open(os.path.join('static', filename), 'rb') as f:
                content = f.read()

            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)

        except FileNotFoundError:
            self.serve_file('error.html', 'text/html', 404)

    def send_to_socket_server(self, username, message):
        """Відправка даних на Socket-сервер"""
        try:
            # Створю UDP socket
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Підготовка даних
            data = {
                'username': username,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }

            # Відправляємо JSON дані
            json_data = json.dumps(data).encode('utf-8')
            client_socket.sendto(json_data, ('localhost', 5000))
            client_socket.close()

            print(f"✅ Повідомлення відправлено на Socket-сервер: {username}")

        except Exception as e:
            print(f"❌ Помилка відправки на Socket-сервер: {e}")


class StudyVaultSocketServer:
    """Socket сервер для обробки повідомлень та збереження в MongoDB"""

    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.mongodb_client = None
        self.database = None
        self.collection = None
        self.setup_mongodb()

    def setup_mongodb(self):
        """Підключення до MongoDB"""
        try:
            # Підключення до MongoDB
            mongodb_url = os.getenv(
                'MONGODB_URL', 'mongodb://localhost:27017/')
            self.mongodb_client = MongoClient(mongodb_url)
            self.database = self.mongodb_client['studyvault']
            self.collection = self.database['messages']

            print("✅ Підключено до MongoDB")

        except Exception as e:
            print(f"❌ Помилка підключення до MongoDB: {e}")

    def start_server(self):
        """Запуск UDP сервера"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((self.host, self.port))

        print(f"🚀 Socket-сервер запущено на {self.host}:{self.port}")

        while True:
            try:
                # Отримує дані
                data, client_address = server_socket.recvfrom(1024)

                # Обробляє в окремому потоці
                thread = threading.Thread(
                    target=self.handle_message,
                    args=(data, client_address)
                )
                thread.daemon = True
                thread.start()

            except Exception as e:
                print(f"❌ Помилка Socket-сервера: {e}")

    def handle_message(self, data, client_address):
        """Обробка повідомлення"""
        try:
            # Декодує JSON дані
            json_data = json.loads(data.decode('utf-8'))

            # Підготовка документу для MongoDB
            document = {
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                'username': json_data['username'],
                'message': json_data['message']
            }

            # Зберігає в MongoDB
            if self.collection is not None:
                result = self.collection.insert_one(document)
                print(
                    f"✅ Повідомлення збережено: {document['username']} - {result.inserted_id}")
            else:
                print("❌ MongoDB не доступна")

        except Exception as e:
            print(f"❌ Помилка обробки повідомлення: {e}")


def create_message_html():
    """Створення message.html"""
    message_html_content = """<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📬 Надіслати повідомлення - StudyVault</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <div class="header-content">
            <h1>📬 Надіслати повідомлення</h1>
            <p>Поділіться своєю думкою з іншими студентами</p>
        </div>
    </header>

    <div class="container">
        <div class="section">
            <h2>✍️ Написати повідомлення</h2>

            <!-- Повідомлення про успіх/помилку -->
            <div id="message-status"></div>

            <form action="/message" method="POST" class="message-form">
                <div class="form-group">
                    <label for="username" class="form-label">Ваше ім'я</label>
                    <input
                        type="text"
                        id="username"
                        name="username"
                        class="form-input"
                        placeholder="Введіть ваше ім'я..."
                        required
                    />
                </div>

                <div class="form-group">
                    <label for="message" class="form-label">Повідомлення</label>
                    <textarea
                        id="message"
                        name="message"
                        class="form-input message-textarea"
                        placeholder="Напишіть ваше повідомлення..."
                        rows="4"
                        required
                    ></textarea>
                </div>

                <button type="submit" class="message-btn">📤 Надіслати повідомлення</button>
            </form>

            <a href="/" class="btn-secondary" style="display: inline-block; margin-top: 1rem;">
                🏠 На головну
            </a>
        </div>
    </div>

    <script>
        // Показуємо повідомлення про результат
        const urlParams = new URLSearchParams(window.location.search);
        const messageStatus = document.getElementById('message-status');

        if (urlParams.get('success') === '1') {
            messageStatus.innerHTML = '<div class="alert alert-success">✅ Повідомлення успішно надіслано!</div>';
        } else if (urlParams.get('error') === '1') {
            messageStatus.innerHTML = '<div class="alert alert-error">❌ Помилка: заповніть всі поля!</div>';
        }

        // Стилі для повідомлень
        const style = document.createElement('style');
        style.textContent = `
            .alert {
                padding: 1rem;
                margin-bottom: 1rem;
                border-radius: 8px;
                font-weight: 600;
            }
            .alert-success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .alert-error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
        `;
        document.head.appendChild(style);
    </script>
</body>
</html>"""

    with open('message.html', 'w', encoding='utf-8') as f:
        f.write(message_html_content)
    print("✅ Створено message.html")


def create_error_html():
    """Створення error.html для 404"""
    error_html_content = """<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>❌ Помилка 404 - StudyVault</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <div class="header-content">
            <h1>❌ Сторінка не знайдена</h1>
            <p>Помилка 404 - Not Found</p>
        </div>
    </header>

    <div class="container">
        <div class="section" style="text-align: center;">
            <h2>🔍 Сторінка не існує</h2>
            <p style="font-size: 1.2rem; margin: 2rem 0;">
                Вибачте, але запитувана сторінка не знайдена.
            </p>

            <div style="margin: 2rem 0;">
                <a href="/" class="btn-primary" style="margin: 0.5rem;">🏠 На головну</a>
                <a href="/message.html" class="btn-secondary" style="margin: 0.5rem;">📬 Повідомлення</a>
            </div>

            <div style="font-size: 3rem; margin: 2rem 0;">📚🔍❓</div>
        </div>
    </div>
</body>
</html>"""

    with open('error.html', 'w', encoding='utf-8') as f:
        f.write(error_html_content)
    print("✅ Створено error.html")


def create_logo_png():
    """Створення логотипу logo.png"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import random

        # Створюємо зображення 128x128
        img = Image.new('RGB', (128, 128), color='#000011')
        draw = ImageDraw.Draw(img)

        # Градієнт фону від темно-синього до фіолетового
        for y in range(128):
            # Градієнт від темно-синього до фіолетового
            progress = y / 128
            r = int(17 + (102 - 17) * progress)      # 11 -> 66 (hex)
            g = int(17 + (30 - 17) * progress)       # 11 -> 1e
            b = int(34 + (138 - 34) * progress)      # 22 -> 8a

            # Додаємо трохи варіації
            r += random.randint(-5, 5)
            g += random.randint(-3, 3)
            b += random.randint(-8, 8)

            # Обмеження кольорів
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))

            draw.line([(0, y), (128, y)], fill=(r, g, b))

        # Додаємо зірки на фон
        for _ in range(25):
            x = random.randint(5, 123)
            y = random.randint(5, 123)
            size = random.randint(1, 2)
            brightness = random.randint(180, 255)
            draw.ellipse([x-size, y-size, x+size, y+size],
                         fill=(brightness, brightness, brightness))

        # Додаємо хрестики зірок
        for _ in range(8):
            x = random.randint(10, 118)
            y = random.randint(10, 118)
            brightness = random.randint(200, 255)
            draw.line([(x-3, y), (x+3, y)], fill=(brightness,
                      brightness, brightness), width=1)
            draw.line([(x, y-3), (x, y+3)], fill=(brightness,
                      brightness, brightness), width=1)
            draw.line([(x-2, y-2), (x+2, y+2)],
                      fill=(brightness, brightness, brightness), width=1)
            draw.line([(x-2, y+2), (x+2, y-2)],
                      fill=(brightness, brightness, brightness), width=1)

        center_x, center_y = 64, 64

        # Сяйво навколо книги
        for radius in range(35, 25, -2):
            alpha = int(50 - (35-radius)*3)
            if alpha > 0:
                glow_color = (102, 126, 234)  # #667eea
                # Імітуємо прозорість через змішування кольорів
                background_color = img.getpixel((center_x, center_y))
                mixed_color = tuple(
                    int(bg + (glow - bg) * alpha / 255)
                    for bg, glow in zip(background_color, glow_color)
                )
                draw.ellipse([center_x-radius, center_y-radius,
                              center_x+radius, center_y+radius],
                             outline=mixed_color, width=1)

        # Книга (основна форма)
        book_width, book_height = 32, 24
        book_left = center_x - book_width // 2
        book_top = center_y - book_height // 2

        # Тінь книги
        draw.rectangle([book_left+2, book_top+2,
                        book_left+book_width+2, book_top+book_height+2],
                       fill=(0, 0, 20))

        # Основа книги (білий фон)
        draw.rectangle([book_left, book_top,
                        book_left+book_width, book_top+book_height], fill=(245, 248, 255))

        # Обкладинка книги (градієнт)
        for i in range(book_height):
            progress = i / book_height
            r = int(102 + (118 - 102) * progress)  # 667eea -> 764ba2
            g = int(126 + (75 - 126) * progress)
            b = int(234 + (162 - 234) * progress)

            draw.line([(book_left, book_top + i),
                      (book_left + book_width, book_top + i)],
                      fill=(r, g, b))

        # Лінії тексту на книзі
        line_color = (255, 255, 255, 200)
        for i, offset in enumerate([6, 10, 14, 18]):
            line_width = book_width - 8 - i * 2
            draw.line([(book_left + 4, book_top + offset),
                      (book_left + 4 + line_width, book_top + offset)],
                      fill=(255, 255, 255), width=1)

        # Закладка
        bookmark_x = book_left + book_width - 2
        draw.rectangle([bookmark_x, book_top,
                        bookmark_x + 4, book_top + book_height + 6],
                       fill=(72, 187, 120))
        # Кінчик закладки
        draw.polygon([bookmark_x, book_top + book_height + 6,
                      bookmark_x + 4, book_top + book_height + 6,
                      bookmark_x + 2, book_top + book_height + 10],
                     fill=(56, 161, 105))

        # Символи "SV" під книгою
        try:
            font_size = 16
            try:
                font = ImageFont.truetype(
                    "/System/Library/Fonts/Helvetica.ttc", font_size)
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()

            text = "SV"
            # Розрахунок позиції для центрування
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            text_x = center_x - text_width // 2
            text_y = center_y + book_height // 2 + 8

            # Тінь тексту
            draw.text((text_x + 1, text_y + 1), text,
                      fill=(0, 0, 50), font=font)
            # Основний текст
            draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)

        except Exception as e:
            # Fallback - малюємо букви вручну простими лініями
            # S
            draw.line([(center_x - 10, center_y + 18), (center_x - 5, center_y + 18)],
                      fill=(255, 255, 255), width=2)
            draw.line([(center_x - 10, center_y + 18), (center_x - 10, center_y + 21)],
                      fill=(255, 255, 255), width=2)
            draw.line([(center_x - 10, center_y + 21), (center_x - 5, center_y + 21)],
                      fill=(255, 255, 255), width=2)
            draw.line([(center_x - 5, center_y + 21), (center_x - 5, center_y + 24)],
                      fill=(255, 255, 255), width=2)
            draw.line([(center_x - 10, center_y + 24), (center_x - 5, center_y + 24)],
                      fill=(255, 255, 255), width=2)

            # V
            draw.line([(center_x + 2, center_y + 18), (center_x + 5, center_y + 24)],
                      fill=(255, 255, 255), width=2)
            draw.line([(center_x + 8, center_y + 18), (center_x + 5, center_y + 24)],
                      fill=(255, 255, 255), width=2)

        for _ in range(12):
            angle = random.random() * 3.14159 * 2
            distance = random.randint(20, 35)
            px = int(center_x + distance * (angle % 1))
            py = int(center_y + distance * ((angle * 1.3) % 1))

            if 5 <= px <= 123 and 5 <= py <= 123:
                brightness = random.randint(150, 255)
                size = random.randint(1, 2)
                draw.ellipse([px-size, py-size, px+size, py+size],
                             fill=(brightness, brightness, brightness))

        img.save('logo.png')
        print("✅ Створено красивий космічний логотип StudyVault")

        # Копіюємо в static
        try:
            import shutil
            shutil.copy('logo.png', 'static/logo.png')
            print("✅ Логотип скопійовано в static/")
        except:
            pass

    except ImportError:
        print("⚠️ PIL недоступна, створюємо простий логотип...")
        # Fallback версія
        simple_png_data = bytes([
            137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82,
            0, 0, 0, 128, 0, 0, 0, 128, 8, 2, 0, 0, 0, 233, 178, 81,
            130, 0, 0, 0, 25, 73, 68, 65, 84, 120, 156, 99, 100, 96, 248,
            79, 193, 128, 137, 129, 129, 37, 0, 0, 14, 48, 1, 225, 39, 222,
            252, 232, 0, 0, 0, 0, 73, 69, 78, 68, 174, 66, 96, 130
        ])

        with open('logo.png', 'wb') as f:
            f.write(simple_png_data)
        print("✅ Створено базовий логотип")

    except Exception as e:
        print(f"❌ Помилка створення логотипу: {e}")
        # Створюємо мінімальний файл
        with open('logo.png', 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\xcc\xdb\x27\x00\x00\x00\x00IEND\xaeB`\x82')
        print("✅ Створено мінімальний логотип")


def main():
    """Головна функція - запуск обох серверів"""
    print("🚀 Запуск StudyVault - Гібридний сервер")

    # Створюємо необхідні файли ТІЛЬКИ якщо їх немає
    if not os.path.exists('templates/message.html'):
        create_message_html()
    if not os.path.exists('templates/error.html') and not os.path.exists('error.html'):
        create_error_html()
    if not os.path.exists('logo.png'):
        create_logo_png()

    # Запуск Socket-сервера в окремому потоці
    socket_server = StudyVaultSocketServer()
    socket_thread = threading.Thread(target=socket_server.start_server)
    socket_thread.daemon = True
    socket_thread.start()

    # Запуск HTTP-сервера на порту 3000
    http_server = HTTPServer(('localhost', 3000), StudyVaultHTTPHandler)
    print("🌐 HTTP-сервер запущено на http://localhost:3000")

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Сервер зупинено")
        http_server.server_close()


if __name__ == "__main__":
    main()
