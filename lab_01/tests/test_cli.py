import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def running_command(tmp_path: Path, *arguments: str) -> subprocess.CompletedProcess:
    """Запускает команду toolkit в отдельном процессе для проверки CLI.

    В tmp_path передаётся временная папка, в arguments — аргументы команды.
    Домашний и рабочий каталоги процесса направляются во временную папку,
    чтобы тест не затрагивал настоящую историю пользователя. PYTHONPATH
    указывает на исходники проекта. Возвращает объект с кодом завершения,
    обычным выводом stdout и выводом ошибок stderr.
    """
    environment: dict[str, str] = os.environ.copy()
    environment["HOME"] = str(tmp_path)
    environment["USERPROFILE"] = str(tmp_path)
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")

    return subprocess.run(
        [sys.executable, "-m", "toolkit", *arguments],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False
    )


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [(("calc", "2 + 3 * 4"), "14"), (("calc", "-2 * (3 + 4)"), "-14"),
     (("convert", "1", "--from", "KM", "--to", "m"), "1000.0"),
     (("convert", "-1e2", "--from", "c", "--to", "k"), "173.15")]
)
def test_cli_success(tmp_path: Path, arguments: tuple, expected: str) -> None:
    """Проверяет успешное выполнение команды через командную строку.

    tmp_path задаёт временную папку, arguments — команду, expected — ответ.
    Проверяются код 0, правильный текст результата, пустой stderr
    и наличие ровно одной записи в файле истории.
    """
    result = running_command(tmp_path, *arguments)

    assert result.returncode == 0
    assert result.stdout.strip() == expected
    assert result.stderr == ""
    assert len(json.loads((tmp_path / "toolkit_history.json").read_text())) == 1


@pytest.mark.parametrize(
    "arguments",
    [("calc", ""), ("calc", "1+"), ("calc", "2@3"), ("calc", "2**3"), ("calc", "1/0"),
     ("convert", "abc", "--from", "m", "--to", "cm"),
     ("convert", "1", "--from", "m", "--to", "kg"),
     ("convert", "1", "--from", "bad", "--to", "m"),
     ("convert", "-1", "--from", "k", "--to", "c"), ("convert", "1"), ()]
)
def test_cli_error(tmp_path: Path, arguments: tuple) -> None:
    """Проверяет, как CLI сообщает о неверной команде или данных.

    В arguments pytest передаёт ошибочный пример, а tmp_path изолирует файлы.
    Ожидаются код 2 и сообщение в stderr без подробного стека Python.
    Обычный вывод должен быть пустым, а файл истории не должен создаваться.
    """
    result = running_command(tmp_path, *arguments)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "toolkit_history.json").exists()


def test_cli_help(tmp_path: Path) -> None:
    """Проверяет вывод справки по флагу --help.

    Запускает CLI во временной папке tmp_path. Проверяет код 0,
    наличие обеих команд в справке и отсутствие сообщения об ошибке.
    Просмотр справки не должен создавать файл истории.
    """
    result = running_command(tmp_path, "--help")

    assert result.returncode == 0
    assert "calc" in result.stdout
    assert "convert" in result.stdout
    assert result.stderr == ""
    assert not (tmp_path / "toolkit_history.json").exists()


def test_history_contains_only_successful_operations(tmp_path: Path) -> None:
    """Проверяет, что история пополняется только после успешных операций.

    В папке tmp_path запускаются два правильных вычисления и деление на ноль.
    В истории должны остаться две записи. Дополнительно проверяются
    содержимое записи калькулятора и результат конвертации.
    """
    running_command(tmp_path, "calc", "0.1+0.2")
    running_command(tmp_path, "calc", "1/0")
    running_command(tmp_path, "convert", "1", "--from", "m", "--to", "cm")
    history = json.loads((tmp_path / "toolkit_history.json").read_text())

    assert len(history) == 2
    assert history[0] == {"command": "calc", "expression": "0.1+0.2", "result": "0.3"}
    assert history[1]["result"] == 100.0


def test_corrupted_history_is_preserved(tmp_path: Path) -> None:
    """Проверяет сохранность повреждённого файла истории.

    В папке tmp_path создаётся файл с текстом, который не является JSON.
    При обычном вычислении программа должна вернуть код 2, не вывести
    результат и оставить содержимое этого файла без изменений.
    """
    path = tmp_path / "toolkit_history.json"
    path.write_text("broken", encoding="utf-8")
    result = running_command(tmp_path, "calc", "1+1")

    assert result.returncode == 2
    assert result.stdout == ""
    assert path.read_text() == "broken"


@pytest.mark.parametrize(
    "arguments",
    [("calc", "2+2"), ("convert", "1", "--from", "m", "--to", "cm")]
)
def test_disabled_history_does_not_create_file(tmp_path: Path, arguments: tuple) -> None:
    """Проверяет отсутствие записи при использовании флага --no-history.

    arguments содержит команду калькулятора или конвертера, а tmp_path —
    временную папку. Команда должна успешно вывести результат,
    но не создавать файл истории.
    """
    result = running_command(tmp_path, "--no-history", *arguments)

    assert result.returncode == 0
    assert result.stdout.strip()
    assert result.stderr == ""
    assert not (tmp_path / "toolkit_history.json").exists()


@pytest.mark.parametrize("contents", ["[]", "broken"])
def test_disabled_history_does_not_read_or_change_file(tmp_path: Path, contents: str) -> None:
    """Проверяет работу без истории при уже существующем файле.

    В tmp_path записывается contents: пустой JSON-массив или повреждённый текст.
    С флагом --no-history вычисление должно пройти успешно в обоих случаях.
    Проверяется результат и то, что содержимое файла осталось прежним.
    """
    path = tmp_path / "toolkit_history.json"
    path.write_text(contents, encoding="utf-8")
    result = running_command(tmp_path, "--no-history", "calc", "-2 * 3")

    assert result.returncode == 0
    assert result.stdout.strip() == "-6"
    assert result.stderr == ""
    assert path.read_text() == contents


def test_custom_history_path_is_rejected(tmp_path: Path) -> None:
    """Проверяет, что путь истории нельзя задать аргументом команды.

    В папке tmp_path выбирается посторонний путь и передаётся через --history.
    CLI должен отклонить неизвестный параметр с кодом 2.
    Ни выбранный файл, ни обычная история не должны появиться.
    """
    path = tmp_path / "custom.json"
    result = running_command(tmp_path, "--history", str(path), "calc", "2+2")

    assert result.returncode == 2
    assert not path.exists()
    assert not (tmp_path / "toolkit_history.json").exists()


def test_history_environment_variable_is_ignored(tmp_path: Path, monkeypatch) -> None:
    """Проверяет, что TOOLKIT_HISTORY не меняет место сохранения истории.

    tmp_path задаёт временную папку. Средство pytest под названием monkeypatch
    временно устанавливает переменную окружения. После вычисления история
    должна появиться по стандартному пути, а не по значению этой переменной.
    """
    path = tmp_path / "custom.json"
    monkeypatch.setenv("TOOLKIT_HISTORY", str(path))
    result = running_command(tmp_path, "calc", "2+2")

    assert result.returncode == 0
    assert not path.exists()
    assert (tmp_path / "toolkit_history.json").exists()


def test_history_path_does_not_depend_on_working_directory(tmp_path: Path, monkeypatch) -> None:
    """Проверяет использование одной истории при запуске из разных папок.

    tmp_path служит временным домашним каталогом. monkeypatch временно меняет
    переменные окружения и рабочую папку. Два вызова main должны добавить
    записи в один домашний файл, не создавая историю в рабочих папках.
    После теста pytest отменяет изменения окружения и текущего каталога.
    """
    from toolkit.__main__ import main

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    for name in ("first", "second"):
        directory = tmp_path / name
        directory.mkdir()
        monkeypatch.chdir(directory)

        assert main(["calc", "2+2"]) == 0
        assert not (directory / "toolkit_history.json").exists()

    history = json.loads((tmp_path / "toolkit_history.json").read_text())

    assert len(history) == 2
