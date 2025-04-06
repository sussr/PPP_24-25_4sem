
def main():
    try:
        # Запуск сервера
        print("[INFO] Запуск сервера...")
        server_proc = subprocess.Popen([sys.executable, 'server.py'])
        time.sleep(2)  # Подождать немного, чтобы сервер успел стартовать

        # Запуск клиента
        print("[INFO] Запуск клиента...")
        client_proc = subprocess.Popen([sys.executable, 'client.py'])

        # Ожидаем завершения клиента
        client_proc.wait()

    except KeyboardInterrupt:
        print("\n[INFO] Прерывание пользователем. Завершение процессов...")
    finally:
        # Завершаем сервер при выходе
        print("[INFO] Завершение сервера...")
        try:
            if server_proc.poll() is None:
                os.kill(server_proc.pid, signal.SIGTERM)
        except Exception as e:
            print(f"[WARN] Не удалось завершить сервер: {e}")


if __name__ == "__main__":
    main()

