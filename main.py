import argparse
import application.client as app
import application.errors as errors


def set_up_arguments(arg_parser):
    data_type = arg_parser.add_mutually_exclusive_group()
    arg_parser.add_argument("url", type=str, help="Ссылка на ресурс.")
    arg_parser.add_argument("-a", "--agent", type=str, help="Указать свой USER-AGENT.", default="Mozilla/5.0")
    arg_parser.add_argument("-o", "--output", type=str, metavar="FILENAME",
                            help="Записывает ответ от сервера в указанный файл.")
    data_type.add_argument("-d", "--data", type=str, default="",
                           help="Данные, введённые в консоль, будут отправлены на web-сервер методом POST.")
    arg_parser.add_argument("-M", "--method", type=str, choices=["GET", "POST", "HEAD", "OPTIONS"], metavar="METHOD",
                            help="Задает тип запроса во время обмена с HTTP сервером.", default="GET")
    data_type.add_argument("-U", "--upload", type=str, metavar="FILENAME",
                           help="Передает содержимое указанного файла на web-сервер методом POST.")
    arg_parser.add_argument("-H", "--header", type=str, nargs=2, action="append", default=[],
                            help="Изменить или добавить заголовок (требует 2 аргумента). Формат ввода: <header> <value>")
    arg_parser.add_argument("-v", "--verbose", action="store_true",
                            help="Выводит отправляемые заголовки на консоль.")
    arg_parser.add_argument("-i", "--include", action="store_true",
                            help="Выводить ответ от сервера полностью/только message body (по умолчанию body)")
    arg_parser.add_argument("-r", "--redirect", action="store_true",
                            help="Включить/ыключить перенаправление на сайты, указанные в 'Location:'")
    arg_parser.add_argument("-T", "--timeout", type=float, metavar="TIME", default=None,
                            help="Устанавливает тайм-аут для подключения к web-серверу")


def extract_arguments(args) -> list:
    if args.data or args.upload:
        args.method = "POST"
    if args.method == "HEAD" or args.method == "OPTIONS":
        args.include = True
    return [args.url, args.method, args.data, args.upload, args.output,
            args.include, args.header, args.verbose, args.agent, args.timeout, args.redirect]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    set_up_arguments(parser)
    cmd_args = extract_arguments(parser.parse_args())
    try:
        client = app.Client(*cmd_args)
        server_response = client.send_request()
        client.get_results(server_response)
    except errors.APIError as e:
        print(str(e))
        exit()
    except Exception as e:
        print(f'{type(e)}: {str(e)}')
        exit()
