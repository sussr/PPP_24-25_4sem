#!/usr/bin/env python3
"""
Клиент для запроса аудиофайлов у сервера.
Позволяет получить список доступных аудиофайлов или запросить отрезок аудио.
"""

import socket
import logging
import json
import struct
import argparse

# Конфигурация логирования
logging.basicConfig(
    level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s'
)


def get_audio_list(sock):
    """
    Запрашивает список аудиофайлов у сервера и выводит его.
    """
    try:
        sock.sendall("LIST\n".encode('utf-8'))
        data = sock.recv(4096)
        audio_list = json.loads(data.decode('utf-8'))
        print("Доступные аудиофайлы:")
        for audio in audio_list:
            print(
                f"- {audio['filename']} | Длительность: {audio['duration_sec']} сек | "
                f"Формат: {audio['format']}"
            )
    except Exception as e:
        logging.error("Ошибка получения списка: %s", e)
        print("Не удалось получить список аудиофайлов.")


def get_audio_segment(sock):
    """
    Запрашивает аудио отрезок у сервера и сохраняет его локально.
    Обработка ошибок ввода пользователя.
    """
    try:
        filename = input("Введите имя файла: ").strip()
        start_time = input("Введите время начала (сек): ").strip()
        end_time = input("Введите время окончания (сек): ").strip()
    except Exception as e:
        logging.error("Ошибка ввода: %s", e)
        print("Ошибка ввода, попробуйте снова.")
        return

    command = f"GET {filename} {start_time} {end_time}\n"
    try:
        sock.sendall(command.encode('utf-8'))
    except Exception as e:
        logging.error("Ошибка отправки команды: %s", e)
        print("Не удалось отправить команду серверу.")
        return

    # Сначала принимаем 1 байт статуса
    status = sock.recv(1)
    if not status:
        print("Ошибка: не получен статус от сервера.")
        return

    # Затем принимаем 4 байта, определяющие длину сообщения
    header = sock.recv(4)
    if len(header) < 4:
        print("Ошибка получения заголовка от сервера.")
        return

    data_length = struct.unpack('!I', header)[0]
    received = b""
    while len(received) < data_length:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            received += chunk
        except Exception as e:
            logging.error("Ошибка при получении данных: %s", e)
            print("Ошибка получения данных.")
            return

    if status == b'0':
        # Сообщение об ошибке
        print("Ошибка от сервера:", received.decode('utf-8'))
    elif status == b'1':
        out_filename = f"segment_{filename}"
        try:
            with open(out_filename, 'wb') as f:
                f.write(received)
            print(f"Аудиофрагмент сохранён как '{out_filename}'")
        except Exception as e:
            logging.error("Ошибка сохранения файла: %s", e)
            print("Не удалось сохранить аудиофрагмент.")
    else:
        print("Неизвестный статус, полученный от сервера.")



def parse_arguments():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description="Клиент для запроса аудиофрагментов у сервера."
    )
    parser.add_argument(
        '--host', type=str, default='127.0.0.1',
        help="IP адрес сервера (по умолчанию '127.0.0.1')"
    )
    parser.add_argument(
        '--port', type=int, default=5000,
        help="Порт сервера (по умолчанию 5000)"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect((args.host, args.port))
            logging.info("Подключение к серверу %s:%s установлено", args.host, args.port)
        except Exception as e:
            logging.error("Ошибка подключения: %s", e)
            print("Не удалось подключиться к серверу.")
            return

        while True:
            print("\nКоманды:")
            print("1. LIST - получить список аудиофайлов")
            print("2. GET  - запросить аудио отрезок")
            print("3. EXIT - выход")
            choice = input("Введите команду: ").strip().upper()
            if choice in ('LIST', '1'):
                get_audio_list(sock)
            elif choice in ('GET', '2'):
                get_audio_segment(sock)
            elif choice in ('EXIT', '3'):
                logging.info("Отключение от сервера.")
                break
            else:
                print("Неверная команда. Попробуйте ещё раз.")


if __name__ == '__main__':
    main()
