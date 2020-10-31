import argparse
import sys
import http_client.errors
import logging
from http_client.client import Client
from http_client.models import OutputMode

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="[%(levelname)s]: %(asctime)s | in %(name)s | %(message)s",
    level=logging.DEBUG,
)


def set_up_arguments(arg_parser):
    data_type = arg_parser.add_mutually_exclusive_group()
    arg_parser.add_argument("url", type=str, help="Ссылка на ресурс.")
    arg_parser.add_argument(
        "-a",
        "--agent",
        type=str,
        help="Указать свой USER-AGENT.",
        default="Mozilla/5.0",
    )
    arg_parser.add_argument(
        "-o",
        "--output",
        type=str,
        metavar="FILENAME",
        help="Записывает ответ от сервера в указанный файл.",
    )
    data_type.add_argument(
        "-d",
        "--data",
        type=str,
        default="",
        help="Данные будут отправлены на web-сервер методом POST.",
    )
    arg_parser.add_argument(
        "-M",
        "--method",
        type=str,
        choices=["GET", "POST", "HEAD", "OPTIONS"],
        metavar="METHOD",
        help="Задает тип запроса во время обмена с HTTP сервером.",
        default="GET",
    )
    data_type.add_argument(
        "-U",
        "--upload",
        type=str,
        metavar="FILENAME",
        help="Передает содержимое файла на web-сервер методом POST.",
    )
    arg_parser.add_argument(
        "-H",
        "--header",
        type=str,
        nargs=2,
        action="append",
        default=[],
        help="Изменить или добавить заголовок. Формат: <header> <value>",
    )
    arg_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Выводит отправляемые заголовки на консоль.",
    )
    arg_parser.add_argument(
        "-i",
        "--include",
        action="store_true",
        help="Выводить ответ от сервера полностью/только message body",
    )
    arg_parser.add_argument(
        "-r",
        "--redirect",
        action="store_true",
        help="Вкл/выкл перенаправление на сайты, указанные в 'Location:'",
    )
    arg_parser.add_argument(
        "-T",
        "--timeout",
        type=float,
        metavar="TIME",
        default=None,
        help="Устанавливает тайм-аут для подключения к web-серверу",
    )
    arg_parser.add_argument(
        "-c",
        "--cookies",
        type=str,
        metavar="FILENAME",
        help="Отправить cookies из файла на web-сервер.",
    )


def extract_arguments() -> tuple:
    if args.data or args.upload:
        args.method = "POST"
    if args.method == "HEAD" or args.method == "OPTIONS":
        args.include = True
    return (
        args.url,
        args.method,
        args.data,
        args.upload,
        args.include,
        args.header,
        args.verbose,
        args.agent,
        args.timeout,
        args.redirect,
        args.cookies,
    )


def get_output_mode() -> OutputMode:
    if args.verbose:
        return OutputMode.FULL
    if args.include:
        return OutputMode.HEADERS_BODY
    return OutputMode.BODY


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    set_up_arguments(parser)
    args = parser.parse_args()
    cmd_args = extract_arguments()
    try:
        output = sys.stdout.buffer
        if args.output:
            output = open(args.output, "bw")
        logger.info("Initializing client")
        client = Client(*cmd_args)
        server_response = client.send_request()

        mode = get_output_mode()
        output.write(client.request.get_results(mode))
        output.write(server_response.get_results(mode))
        output.close()
    except http_client.errors.APIError as e:
        logger.error(f"Client error occurred: {e}")
    except Exception as e:
        logger.exception(f"Exception of type {type(e)} caught:", e)
    finally:
        logger.info("Closing application")
        exit()
