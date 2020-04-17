import argparse


class ArgumentsCreator:
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    data_type = parser.add_mutually_exclusive_group()

    def set_up_arguments(self):
        self.parser.add_argument("url", type=str, help="Ссылка на ресурс.")
        self.parser.add_argument("-a", "--agent", type=str, help="Указать свой USER_AGENT.", default="Mozilla/5.0")
        self.parser.add_argument("-o", "--output", type=str,
                                 help="Записывает вывод в файл вместо stdout.", metavar="FILENAME")
        self.data_type.add_argument("-d", "--data", type=str,
                                    help="Данные, введённые в консоль, будут отправлены на web-сервер.", default="")
        self.parser.add_argument("-X", "--request", type=str, choices=["GET", "POST", "HEAD"],
                                 help="Задает тип запроса во время обмена с HTTP сервером.", default="GET", metavar="METHOD")
        self.data_type.add_argument("-T", "--upload", type=str,
                                    help="Передает содержимое указанного файла на web-сервер.", metavar="FILENAME")
        self.parser.add_argument("-H", "--header", type=str, nargs=2, action="append", default=[],
                                 help="Изменить или добавить заголовок (требует 2 аргумента). Формат ввода: <header:> <value>")
        self.parser.add_argument("-v", "--verbose", action="store_true",
                                 help="Выводит отправляемые заголовки на консоль.")
        self.parser.add_argument("-m", "--mode", type=str, choices=["all", "body"],
                                 help="Режим вывода ответа от сервера", default="all")
        return self.parser
