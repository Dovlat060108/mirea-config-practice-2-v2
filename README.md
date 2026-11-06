# Практическая работа №2. Вариант 2

Алиев Довлат Фазильевич, ИКБО-62-25.
Дисциплина: «Конфигурационное управление».
Выполнены этапы 1 и 2.

## Описание

Программа получает прямые зависимости Java-пакета из Maven-репозитория.
Все семь настроек читаются из XML. POM загружается по HTTP(S) и разбирается
самостоятельно средствами Python. Maven и библиотеки получения зависимостей
не используются. JAR-файлы не загружаются.

Этап 1: проверка настроек и вывод `ключ=значение`.
Этап 2: получение POM указанной версии и вывод прямых зависимостей.
Граф, обход транзитивных зависимостей и изображения относятся к этапам 3-5.

## Запуск, сборка и тесты

Нужен Python 3.10 или новее, только стандартная библиотека.
Java, Maven и установка Python-пакетов не требуются.
Команды из корня проекта:

```sh
python3 -B src/main.py examples/junit.xml
sh run.sh examples/slf4j.xml
sh run.sh examples/test.xml
make build
make test
make demo-errors
```

`make build` проверяет импорт исходников без создания файлов сборки.
Без make: `PYTHONPATH=src python3 -B -m unittest discover -s tests -v`.
Демонстрация ошибок: `PYTHONPATH=src python3 -B examples/demo_errors.py`.
В PyCharm откройте папку проекта; скрипт запуска - `src/main.py`,
параметр - `examples/junit.xml`, рабочий каталог - корень проекта.

## Настройки XML

Корень документа - `<config>`. Все семь элементов обязательны.
Пример целиком находится в `examples/junit.xml`.

| Элемент | Назначение и допустимое значение |
| --- | --- |
| package | Maven-координаты `groupId:artifactId`, например `junit:junit` |
| repository | Базовый HTTP(S) URL Maven или путь к JSON в тестовом режиме |
| test_mode | Строго `true` или `false`; в тесте package состоит из букв A-Z |
| version | Точная версия, например `4.13.2`, без слешей и пробелов |
| output | Будущий файл `.svg`; родительский каталог должен существовать |
| ascii_tree | `true` или `false`; настройка дерева для этапа 5 |
| filter | Подстрока исключения для этапа 3; пустой элемент отключает фильтр |

Пути считаются от каталога XML. Неизвестные, повторные и вложенные поля
отклоняются. Ошибка любого параметра даёт сообщение в stderr и код 2.
Успешный запуск возвращает 0. На этапе 2 output, ascii_tree и filter
проверяются, но ещё не изменяют результат. Файл SVG не создаётся.

## Примеры результата

```sh
sh run.sh examples/junit.xml
```

Пакет `junit:junit`, версия `4.13.2`:

```text
org.hamcrest:hamcrest-core:1.3
org.hamcrest:hamcrest-library:1.3
```

Программа дополнительно указывает scope, optional, type и classifier.
У hamcrest-core scope=compile, у hamcrest-library scope=test.
Показываются все прямые объявления, включая test, provided и optional.
Это список объявлений POM, поэтому он отличается от runtime classpath.

```sh
sh run.sh examples/slf4j.xml
```

Для `org.slf4j:slf4j-api:2.0.17` выводится `junit:junit:4.13.1`, scope=test.
Для `examples/test.xml` результат - B и C. Узел D не выводится:
он зависит от B и не является прямой зависимостью A.
Пакет без зависимостей даёт строку `(нет)`.

## Как разбирается Maven

Из `groupId:artifactId:version` строится URL вида
`group/id/artifactId/version/artifactId-version.pom`.
Поддержаны XML namespace POM, свойства `${...}`, parent POM,
dependencyManagement и импорт BOM. Parent и BOM загружаются из того же
репозитория. Повторные запросы кешируются в памяти. Циклы parent/BOM,
отсутствующие версии, неизвестные свойства, HTTP 404 и ошибки XML
сообщаются пользователю. Ограничения: 15 секунд на запрос, POM до 4 МиБ.

Читаются непосредственные dependencies проекта с наследованием от parent.
Секции плагинов и dependencyManagement сами по себе в результат не входят.
Зависимости из Maven-профилей не активируются. Это учебный разбор POM,
а не полная реализация effective POM: переопределение ребёнком свойств
уже разрешённых зависимостей родителя не поддерживается.
Версия выбирается точно; диапазоны, LATEST и поиск timestamped SNAPSHOT
по maven-metadata.xml не реализованы. Дополнительные repositories из POM
и локальный relativePath родителя не используются.

## Исходники и функции

- `src/config.py`: Config - настройки; parse_bool - флаги;
  check_package и check_repository - координаты и URL; collect_fields -
  структура XML; read_fields - чтение; check_values - проверка полей;
  load_config - разрешение путей; display_config - вывод этапа 1.
- `src/main.py`: main - аргументы и ошибки; show_dependencies - вывод этапа 2.
- `src/pom.py`: expand - свойства; parse_pom - XML; text - текст поля;
  own_properties - свойства проекта; Dependency.key и display - идентификатор
  и вывод зависимости; Model - данные POM; dependency - разбор объявления;
  project_properties - объединение свойств и координат проекта.
- `src/maven.py`: pom_url - адрес POM; download - HTTP-загрузка;
  Repository.__init__ - репозиторий и кеш; parent_model - родитель;
  managed_dependencies - управляемые версии; model - сбор данных POM;
  direct_dependencies - список прямых зависимостей.
- `src/test_repository.py`: check_graph - проверка JSON-графа;
  direct_test_dependencies - непосредственные соседи выбранного узла.
- `examples/demo_errors.py`: main - семь примеров неверных параметров.

## Проверка

Этап 1 содержит 10 тестов. Этап 2 содержит 30 тестов: настройки, ошибки XML,
HTTP-сервер с POM и 404, свойства, parent, BOM, кеш, циклы, области зависимостей
и локальный граф. Тесты не требуют интернета. Проверены реальные запросы
к Maven Central для JUnit 4.13.2, SLF4J API 2.0.17 и Commons Lang 3.17.0.

## История этапов

Репозиторий: https://github.com/Dovlat060108/mirea-config-practice-2-v2

- `stage-1` - минимальный прототип; запускает вывод семи настроек.
- `stage-2` - сбор данных; запускает вывод прямых зависимостей.
- `main` - последний выполненный этап (этап 2).

Переключение: `git switch stage-1` или `git switch stage-2`.
Каждый этап сохранён отдельным коммитом Conventional Commits.

## Источники

Сборник ПР №2 для ИКБО-62-25, вариант 2, страницы 11-13.
POM: https://maven.apache.org/pom.html
URL POM: https://maven.apache.org/repositories/layout.html
