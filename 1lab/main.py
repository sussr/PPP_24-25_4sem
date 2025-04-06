
def main():
    # Получаем абсолютный путь к текущему каталогу, где лежит main.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(base_dir, "server.py")
    client_path = os.path.join(base_dir, "client.py")

    try:
        print("[INFO] Запуск сервера...")
        server_proc = subprocess.Popen([sys.executable, server_path])
        time.sleep(2)

        print("[INFO] Запуск клиента...")
        client_proc = subprocess.Popen([sys.executable, client_path])

        client_proc.wait()

    except KeyboardInterrupt:
        print("\n[INFO] Прерывание пользователем.")
    finally:
        print("[INFO] Завершение сервера...")
        try:
            if server_proc and server_proc.poll() is None:
                server_proc.terminate()
                server_proc.wait(timeout=5)
        except Exception as e:
            print(f"[WARN] Не удалось завершить сервер: {e}")

if __name__ == '__main__':
    main()


if __name__ == "__main__":
    main()

