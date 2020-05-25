import argparse
import application.client as app
import application.errors as errors


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    set_up_arguments(parser)
    cmd_args = extract_args(parser.parse_args())
    try:
        if cmd_args["URL"].startswith('https'):
            client = app.ClientSecured(cmd_args)
        else:
            client = app.Client(cmd_args)
        server_response = client.send_request()
        client.get_results(server_response)
    except errors.APIError as e:
        print(str(e))
        exit()
    except Exception as e:
        print(f'{type(e)}: {str(e)}')
        exit()


def set_up_arguments(parser):
    data_type = parser.add_mutually_exclusive_group()
    parser.add_argument("url", type=str, help="Ссылка на ресурс.")
    parser.add_argument("-a", "--agent", type=str, help="Указать свой USER_AGENT.", default="Mozilla/5.0")
    parser.add_argument("-o", "--output", type=str, metavar="FILENAME",
                        help="Записывает message body в указанный файл.")
    data_type.add_argument("-d", "--data", type=str, default="",
                           help="Данные, введённые в консоль, будут отправлены на web-сервер методом POST.")
    parser.add_argument("-M", "--method", type=str, choices=["GET", "POST", "HEAD", "OPTIONS"], metavar="METHOD",
                        help="Задает тип запроса во время обмена с HTTP сервером.", default="GET")
    data_type.add_argument("-U", "--upload", type=str, metavar="FILENAME",
                           help="Передает содержимое указанного файла на web-сервер методом POST.")
    parser.add_argument("-H", "--header", type=str, nargs=2, action="append", default=[],
                        help="Изменить или добавить заголовок (требует 2 аргумента). Формат ввода: <header> <value>")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Выводит отправляемые заголовки на консоль.")
    parser.add_argument("-m", "--mode", type=str, choices=["all", "body"], default="body",
                        help="Выводить ответ от сервера полностью/только message body (по умолчанию body)")


def extract_args(args) -> dict:
    return {
        "Agent": args.agent,
        "URL": args.url,
        "Method": args.method,
        "Data": args.data,
        "Output": args.output,
        "Mode": args.mode,
        "Headers": args.header,
        "Verbose": args.verbose,
        "Upload": args.upload
    }


if __name__ == '__main__':
    main()
