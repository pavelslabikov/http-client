Автор задачи: Слабиков Павел, КБ-101
Данный HTTP клиент позволяет отправлять запросы на web-сервера при помощи запросов: GET, POST, HEAD

Использование: client.py [-h] [-a AGENT] [-m {all,body}] [-o OUTPUT] [-p PARAMS | -d DATA | -I] URL

Справка по ключам:  
-h, --help                        show this help message and exit

-a AGENT, --agent AGENT           Указать свой USER_AGENT
                        
-m {all,body}, --mode {all,body}  Режим вывода ответа от сервера (полностью, или только тело сообщения)
                        
-o OUTPUT, --output OUTPUT        Записывает вывод в файл вместо stdout.
                        
-p PARAMS, --params PARAMS        Указать GET-параметры
                        
-d DATA, --data DATA              Отправить данные методом POST

-I, --head                        Отправить запрос при помощи метода HEAD

