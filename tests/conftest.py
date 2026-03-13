"""Фикстуры для тестов gitlab.py"""

import pytest
import os
import shutil
from unittest.mock import Mock, MagicMock, patch

@pytest.fixture
def mock_gitlab_token():
    """Мок-токен GitLab"""
    return "fake-token-12345"

@pytest.fixture
def mock_response():
    """Базовый мок-ответ"""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = {}
    return mock

@pytest.fixture
def mock_group_response():
    """Мок-ответ для одной группы"""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = {
        "id": 123,
        "name": "Test Group",
        "full_path": "parent/test-group",
        "projects": []
    }
    return mock

@pytest.fixture
def mock_groups_list_response():
    """Мок-ответ для списка групп"""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = [
        {"id": 1, "name": "Group 1", "full_path": "group1"},
        {"id": 2, "name": "Group 2", "full_path": "group2"},
    ]
    return mock

@pytest.fixture
def mock_subgroups_response():
    """Мок-ответ для подгрупп"""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = [
        {"id": 11, "name": "Subgroup 1", "full_path": "group1/sub1"},
        {"id": 12, "name": "Subgroup 2", "full_path": "group1/sub2"},
    ]
    return mock

@pytest.fixture
def mock_projects_response():
    """Мок-ответ для проектов"""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = [
        {"id": 101, "name": "Project 1", "path": "proj1"},
        {"id": 102, "name": "Project 2", "path": "proj2"},
    ]
    return mock

@pytest.fixture
def mock_projects_page1_response():
    """Мок-ответ для первой страницы проектов"""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = [{"id": i, "name": f"Project {i}"} for i in range(100)]
    return mock

@pytest.fixture
def mock_projects_page2_response():
    """Мок-ответ для второй страницы проектов"""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = [{"id": i, "name": f"Project {i}"} for i in range(100, 150)]
    return mock

@pytest.fixture
def mock_branches_response():
    """Мок-ответ для веток"""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = [
        {"name": "main", "default": True, "protected": True},
        {"name": "develop", "default": False, "protected": False},
    ]
    return mock

@pytest.fixture
def mock_logger():
    """Мок для логгера"""
    mock = MagicMock()
    mock.info = MagicMock()
    mock.debug = MagicMock()
    mock.warning = MagicMock()
    mock.error = MagicMock()
    mock.critical = MagicMock()
    return mock

@pytest.fixture
def mock_session_get(mocker):
    """Мок для session.get"""
    return mocker.patch('requests.Session.get')

@pytest.fixture(autouse=True)
def cleanup_logs():
    """
    Фикстура для очистки логов после тестов.
    Просто чистим файлы и сбрасываем синглтон.
    """
    # Удаляем старые логи если есть
    if os.path.exists('logs'):
        shutil.rmtree('logs')

    yield  # здесь выполняется тест

    # Очищаем после теста
    if os.path.exists('logs'):
        shutil.rmtree('logs')
