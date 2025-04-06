#!/usr/bin/env python3
"""
Сервер для работы с аудиофайлами.
При запуске сканирует заданную директорию, сохраняет метаданные в JSON,
принимает подключения клиентов и обрабатывает их запросы.
"""

import os
import json
import logging
import socket
import threading
import tempfile
import struct
import argparse

from pydub import AudioSegment

# Конфигурация логирования
logging.basicConfig(
    level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s'
)

# Список поддерживаемых аудио расширений
SUPPORTED_EXTENSIONS = ('.wav', '.mp3', '.ogg', '.flac')


def load_audio_metadata(audio_dir, metadata_file):
    """
    Сканирует директорию с аудиофайлами, собирает метаданные и сохраняет их в JSON-файл.
    Если директория не существует, создаёт её.
    """
    metadata_list = []

    if not os.path.exists(audio_dir):
        logging.warning("Директория '%s' не найдена. Создаю новую.", audio_dir)
        try:
            os.makedirs(audio_dir)
        except Exception as exc:
            logging.error("Не удалось создать директорию '%s': %s", audio_dir, exc)
            return metadata_list

    for filename in os.listdir(audio_dir):
        if filename.lower().endswith(SUPPORTED_EXTENSIONS):
            file_path = os.path.join(audio_dir, filename)
            try:
                audio = AudioSegment.from_file(file_path)
                duration_sec = round(len(audio) / 1000.0, 2)  # длительность в секундах
                file_format = os.path.splitext(filename)[1][1:]
                metadata_list.append({
                    'filename': filename,
                    'duration_sec': duration_sec,
                    'format': file_format
                })
            except Exception as e:
                logging.error("Ошибка обработки файла '%s': %s", filename, e)

    try:
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata_list, f, indent=4)
        logging.info("Метаданные сохранены в '%s'", metadata_file)
    except Exception as e:
        logging.error("Ошибка сохранения метаданных: %s", e)
    return metadata_list


def handle_client(conn, addr, audio_dir, metadata_list):
    """
    Обработка запросов от подключившегося клиента.
    Поддерживаемые команды:
    - LIST: отправка списка аудиофайлов с метаданными;
    - GET <имя_файла> <начало> <конец>: вырезка указанного отрезка и отправка данных.
    Дополнительные проверки:
    - Проверка корректности количества параметров.
    - Проверка наличия запрошенного файла в списке аудиофайлов.
    - Проверка валидности временных интервалов (числовой формат, неотрицательность,
      а также соответствие длительности файла).
    """
    logging.info("Подключение клиента %s:%s", addr[0], addr[1])
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            command_line = data.decode('utf-8').strip()
            logging.info("Получена команда от %s: %s", addr, command_line)
            parts = command_line.split()
            if not parts:
                err_msg = "Пустой запрос."
                logging.info(err_msg)
                conn.sendall(err_msg.encode('utf-8'))
                continue

            command = parts[0].upper()

            if command == 'LIST':
                # Если у команды LIST есть лишние параметры, отправляем уведомление
                if len(parts) != 1:
                    err_msg = "Команда LIST не принимает параметры."
                    logging.info(err_msg)
                    conn.sendall(err_msg.encode('utf-8'))
                    continue
                response = json.dumps(metadata_list)
                conn.sendall(response.encode('utf-8'))


            elif command == 'GET':

                # Ожидаем ровно 4 параметра: GET, имя_файла, начало, конец

                if len(parts) != 4:
                    err_msg = "Неверный формат команды GET. Используйте: GET <имя_файла> <начало> <конец>"

                    logging.info(err_msg)

                    err_bytes = err_msg.encode('utf-8')

                    # Отправляем статус ошибки (0) + длину сообщения + само сообщение

                    conn.sendall(b'0' + struct.pack('!I', len(err_bytes)) + err_bytes)

                    continue

                filename = parts[1]

                # Проверка, что имя файла присутствует в списке метаданных

                if not any(item['filename'] == filename for item in metadata_list):
                    err_msg = f"Файл '{filename}' не найден."

                    logging.info(err_msg)

                    err_bytes = err_msg.encode('utf-8')

                    conn.sendall(b'0' + struct.pack('!I', len(err_bytes)) + err_bytes)

                    continue

                try:

                    start_sec = float(parts[2])

                    end_sec = float(parts[3])

                except ValueError:

                    err_msg = "Параметры времени должны быть числами."

                    logging.info(err_msg)

                    err_bytes = err_msg.encode('utf-8')

                    conn.sendall(b'0' + struct.pack('!I', len(err_bytes)) + err_bytes)

                    continue

                if start_sec < 0 or end_sec < 0:
                    err_msg = "Временные параметры не могут быть отрицательными."

                    logging.info(err_msg)

                    err_bytes = err_msg.encode('utf-8')

                    conn.sendall(b'0' + struct.pack('!I', len(err_bytes)) + err_bytes)

                    continue

                file_path = os.path.join(audio_dir, filename)

                if not os.path.exists(file_path):
                    err_msg = f"Файл '{filename}' не найден в файловой системе."

                    logging.info(err_msg)

                    err_bytes = err_msg.encode('utf-8')

                    conn.sendall(b'0' + struct.pack('!I', len(err_bytes)) + err_bytes)

                    continue

                try:

                    audio = AudioSegment.from_file(file_path)

                    file_duration_sec = len(audio) / 1000.0

                except Exception as e:

                    err_msg = f"Ошибка чтения аудиофайла: {e}"

                    logging.info(err_msg)

                    err_bytes = err_msg.encode('utf-8')

                    conn.sendall(b'0' + struct.pack('!I', len(err_bytes)) + err_bytes)

                    continue

                if start_sec >= end_sec:
                    err_msg = "Начальное время должно быть меньше конечного."

                    logging.info(err_msg)

                    err_bytes = err_msg.encode('utf-8')

                    conn.sendall(b'0' + struct.pack('!I', len(err_bytes)) + err_bytes)

                    continue

                if end_sec > file_duration_sec:
                    err_msg = f"Конечное время ({end_sec} сек) превышает длительность файла ({file_duration_sec} сек)."

                    logging.info(err_msg)

                    err_bytes = err_msg.encode('utf-8')

                    conn.sendall(b'0' + struct.pack('!I', len(err_bytes)) + err_bytes)

                    continue

                try:

                    start_ms = int(start_sec * 1000)

                    end_ms = int(end_sec * 1000)

                    segment = audio[start_ms:end_ms]

                    suffix = os.path.splitext(filename)[1]

                    # Создание временного файла без блокировки (delete=False)

                    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)

                    tmp_name = tmp.name

                    tmp.close()

                    try:

                        segment.export(tmp_name, format=suffix[1:])

                        with open(tmp_name, 'rb') as f:

                            segment_data = f.read()

                    finally:

                        os.remove(tmp_name)

                    # Отправляем статус успеха (1), длину аудиоданных и сами данные

                    conn.sendall(b'1' + struct.pack('!I', len(segment_data)) + segment_data)

                    logging.info(

                        "Отправлен аудио отрезок '%s' (%d байт) клиенту %s",

                        filename, len(segment_data), addr

                    )

                except Exception as e:

                    err_msg = f"Ошибка обработки аудио: {e}"

                    logging.info(err_msg)

                    err_bytes = err_msg.encode('utf-8')

                    conn.sendall(b'0' + struct.pack('!I', len(err_bytes)) + err_bytes)
            else:
                err_msg = f"Неизвестная команда: {command}"
                logging.info(err_msg)
                conn.sendall(err_msg.encode('utf-8'))
    except Exception as e:
        logging.error("Ошибка в обработке клиента %s: %s", addr, e)
    finally:
        conn.close()
        logging.info("Закрыто соединение с клиентом %s:%s", addr[0], addr[1])


def start_server(audio_dir, host, port):
    """
    Запускает сервер, создаёт список метаданных и принимает подключения.
    """
    metadata_file = os.path.join(audio_dir, 'metadata.json')
    metadata_list = load_audio_metadata(audio_dir, metadata_file)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.bind((host, port))
    except Exception as e:
        logging.error("Ошибка привязки к %s:%s - %s", host, port, e)
        return

    server_socket.listen(5)
    logging.info("Сервер запущен на %s:%s", host, port)

    try:
        while True:
            conn, addr = server_socket.accept()
            client_thread = threading.Thread(
                target=handle_client, args=(conn, addr, audio_dir, metadata_list)
            )
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        logging.info("Сервер остановлен вручную.")
    except Exception as e:
        logging.error("Ошибка сервера: %s", e)
    finally:
        server_socket.close()


def parse_arguments():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="Сервер аудиофайлов с функционалом вырезки отрезков."
    )
    parser.add_argument(
        '--audio_dir', type=str, default='audio_files',
        help="Путь к директории с аудиофайлами (по умолчанию 'audio_files')"
    )
    parser.add_argument(
        '--host', type=str, default='0.0.0.0',
        help="Адрес для прослушивания (по умолчанию '0.0.0.0')"
    )
    parser.add_argument(
        '--port', type=int, default=5000,
        help="Порт для прослушивания (по умолчанию 5000)"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    start_server(args.audio_dir, args.host, args.port)


if __name__ == '__main__':
    main()
