import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def running_command(tmp_path: Path, *arguments: str) -> subprocess.CompletedProcess:
    """Запускает toolkit отдельным процессом и возвращает код завершения, stdout и
    stderr.

    HOME и рабочая папка указывают на tmp_path, чтобы тесты не трогали
    настоящую историю. PYTHONPATH ведёт в исходники проекта.
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
    """Удачная команда: код 0, нужный вывод, пустой stderr и ровно одна запись в
    истории.
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
    """Ошибочная команда: код 2, сообщение в stderr без трейсбека, пустой stdout и
    ни одного файла истории.
    """
    result = running_command(tmp_path, *arguments)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "toolkit_history.json").exists()


def test_cli_help(tmp_path: Path) -> None:
    """--help: код 0, в справке обе команды, ошибок нет, история не создаётся.
    """
    result = running_command(tmp_path, "--help")

    assert result.returncode == 0
    assert "calc" in result.stdout
    assert "convert" in result.stdout
    assert result.stderr == ""
    assert not (tmp_path / "toolkit_history.json").exists()


def test_history_contains_only_successful_operations(tmp_path: Path) -> None:
    """Два удачных вычисления и одно деление на ноль: в истории остаются две
    записи.

    Заодно проверяется содержимое записей калькулятора и конвертера.
    """
    running_command(tmp_path, "calc", "0.1+0.2")
    running_command(tmp_path, "calc", "1/0")
    running_command(tmp_path, "convert", "1", "--from", "m", "--to", "cm")
    history = json.loads((tmp_path / "toolkit_history.json").read_text())

    assert len(history) == 2
    assert history[0] == {"command": "calc", "expression": "0.1+0.2", "result": "0.3"}
    assert history[1]["result"] == 100.0


def test_corrupted_history_is_preserved(tmp_path: Path) -> None:
    """Повреждённый файл истории не перезаписывается.

    Ожидается код 2, пустой stdout и прежнее содержимое файла.
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
    """С --no-history команда печатает результат, но файл истории не создаётся.
    """
    result = running_command(tmp_path, "--no-history", *arguments)

    assert result.returncode == 0
    assert result.stdout.strip()
    assert result.stderr == ""
    assert not (tmp_path / "toolkit_history.json").exists()


@pytest.mark.parametrize("contents", ["[]", "broken"])
def test_disabled_history_does_not_read_or_change_file(tmp_path: Path, contents: str) -> None:
    """С --no-history существующий файл истории не читается и не меняется.

    contents - пустой JSON-массив или мусор, команда работает в обоих случаях.
    """
    path = tmp_path / "toolkit_history.json"
    path.write_text(contents, encoding="utf-8")
    result = running_command(tmp_path, "--no-history", "calc", "-2 * 3")

    assert result.returncode == 0
    assert result.stdout.strip() == "-6"
    assert result.stderr == ""
    assert path.read_text() == contents


def test_custom_history_path_is_rejected(tmp_path: Path) -> None:
    """Параметра --history не существует: CLI отвечает кодом 2.

    Ни указанный файл, ни обычная история не появляются.
    """
    path = tmp_path / "custom.json"
    result = running_command(tmp_path, "--history", str(path), "calc", "2+2")

    assert result.returncode == 2
    assert not path.exists()
    assert not (tmp_path / "toolkit_history.json").exists()


def test_history_environment_variable_is_ignored(tmp_path: Path, monkeypatch) -> None:
    """Переменная TOOLKIT_HISTORY ни на что не влияет.

    История по-прежнему пишется в стандартное место.
    """
    path = tmp_path / "custom.json"
    monkeypatch.setenv("TOOLKIT_HISTORY", str(path))
    result = running_command(tmp_path, "calc", "2+2")

    assert result.returncode == 0
    assert not path.exists()
    assert (tmp_path / "toolkit_history.json").exists()


def test_history_path_does_not_depend_on_working_directory(tmp_path: Path, monkeypatch) -> None:
    """История одна на пользователя, из какой бы папки ни запустили команду.

    Два вызова main из разных рабочих папок пишут в один файл в домашнем
    каталоге и ничего не создают в самих папках. tmp_path играет роль домашнего
    каталога, monkeypatch подменяет окружение и текущую папку.
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
