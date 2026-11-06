# Практическая работа №2. Вариант 2. Этап 1

Алиев Довлат Фазильевич, ИКБО-62-25.
Дисциплина: «Конфигурационное управление».

## Что сделано

Прототип инструмента анализа зависимостей Maven. Программа читает XML,
проверяет семь настроек и выводит их в формате `ключ=значение`.
Ошибки выводятся в stderr; код завершения при ошибке равен 2.
На первом этапе обращения к Maven и построения графа ещё нет.

## Запуск, сборка и тесты

Нужен Python 3.10 или новее. Используется только стандартная библиотека.
Maven, Java и дополнительные Python-пакеты устанавливать не нужно.
Все команды выполняются из корня проекта:

```sh
python3 -B src/main.py examples/junit.xml
sh run.sh examples/test.xml
make build
make test
make demo-errors
```

`make build` проверяет импорт исходников; отдельная компиляция не нужна.
Без make: `PYTHONPATH=src python3 -B -m unittest discover -s tests -v`.
Демонстрация ошибок: `PYTHONPATH=src python3 -B examples/demo_errors.py`.

## Настройки XML

Корень документа: `<config>`. Все семь элементов обязательны.
Неизвестные, повторные и вложенные поля считаются ошибкой.

| Элемент | Назначение и допустимое значение |
| --- | --- |
| package | Maven-координаты `groupId:artifactId`, например `junit:junit` |
| repository | Базовый HTTP(S) URL Maven или путь к файлу в тестовом режиме |
| test_mode | `true` или `false`; в тесте package состоит из букв A-Z |
| version | Точная непустая версия, например `4.13.2`, без слешей и пробелов |
| output | Будущий файл графа `.svg`; родительский каталог должен существовать |
| ascii_tree | `true` или `false`; настройка вывода дерева для этапа 5 |
| filter | Подстрока исключения для этапа 3; пустой элемент отключает фильтр |

Локальные пути считаются от каталога XML, независимо от текущего каталога.
URL с паролем, параметрами запроса или фрагментом не принимается.
На первом этапе настройки output, ascii_tree и filter только проверяются.
Файлы графов не создаются.

## Пример

`examples/junit.xml` задаёт пакет `junit:junit`, версию `4.13.2` и Maven Central.
Начало вывода:

```text
package=junit:junit
repository=https://repo.maven.apache.org/maven2
test_mode=false
version=4.13.2
```

Затем выводятся output (абсолютный путь), ascii_tree и filter.
`examples/test.xml` задаёт пакет A из `examples/graph.json`.
Скрипт `examples/demo_errors.py` показывает ошибки всех семи параметров.

## Исходники и функции

- `src/config.py`: Config хранит настройки; parse_bool разбирает флаги;
  check_package и check_repository проверяют пакет и URL; collect_fields
  проверяет структуру XML; read_fields читает
  XML; check_values проверяет все поля; load_config разрешает пути;
  display_config печатает настройки.
- `src/main.py`: main разбирает путь к XML и обрабатывает ошибки.
- `examples/demo_errors.py`: main демонстрирует ошибки параметров.
- `tests/test_config.py`: 10 тестов XML, путей, настроек и обработки ошибок.

## Этапы

Ветка `stage-1` сохраняет прототип первого этапа.
Следующий этап добавит чтение POM и вывод прямых зависимостей.

## Основание

Сборник ПР №2 для ИКБО-62-25, вариант 2, страницы 11-13.
Описание Maven: https://maven.apache.org/pom.html
Размещение POM в репозитории: https://maven.apache.org/repositories/layout.html
