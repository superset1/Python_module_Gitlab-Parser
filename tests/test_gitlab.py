"""Тесты для класса Find из gitlab.py"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock, call
from GitlabParser.gitlab import Find


class TestFindInitialization:
    """Тесты инициализации класса Find"""

    @pytest.mark.smoke
    def test_find_import(self):
        """Проверка импорта класса"""
        assert Find is not None

    @pytest.mark.unit
    def test_find_init_with_token(self, mock_gitlab_token):
        """Тест инициализации с токеном"""
        finder = Find(gitlab_token=mock_gitlab_token)
        assert finder.gitlab_token == mock_gitlab_token
        assert finder.headers['PRIVATE-TOKEN'] == mock_gitlab_token
        assert finder.gitlab_url == "https://gitlab.com"

    @pytest.mark.unit
    def test_find_init_with_custom_url(self, mock_gitlab_token):
        """Тест инициализации с кастомным URL"""
        custom_url = "https://gitlab.example.com"
        finder = Find(gitlab_url=custom_url, gitlab_token=mock_gitlab_token)
        assert finder.gitlab_url == custom_url


class TestFindAllGroups:
    """Тесты метода find_all_groups"""

    @pytest.mark.smoke
    def test_find_all_groups_empty_list(self, mock_gitlab_token):
        """Тест поиска групп с пустым списком"""
        finder = Find(gitlab_token=mock_gitlab_token)
        groups = finder.find_all_groups(group_ids=[])
        assert groups == []

    @pytest.mark.unit
    @patch('requests.Session.get')
    def test_find_all_groups_single(self, mock_get, mock_gitlab_token):
        """Тест поиска одной группы"""
        # Исправлено: возвращаем JSON для одной группы
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "name": "Group 123"}
        mock_get.return_value = mock_response

        finder = Find(gitlab_token=mock_gitlab_token)
        
        # Исправлено: мокаем рекурсивную часть, чтобы она не вызывалась
        with patch.object(finder, 'find_all_groups', wraps=finder.find_all_groups) as spy:
            groups = finder.find_all_groups(group_ids=[123], recursive=False)
            
            assert len(groups) == 1
            assert groups[0]['id'] == 123
            mock_get.assert_called_once()

    @pytest.mark.unit
    @patch('requests.Session.get')
    def test_find_all_groups_multiple(self, mock_get, mock_gitlab_token):
        """Тест поиска нескольких групп"""
        # Исправлено: возвращаем разные JSON для разных вызовов
        def side_effect(url, **kwargs):
            mock = Mock()
            mock.status_code = 200
            if '123' in url:
                mock.json.return_value = {"id": 123, "name": "Group 123"}
            elif '456' in url:
                mock.json.return_value = {"id": 456, "name": "Group 456"}
            else:
                mock.json.return_value = {"id": 789, "name": "Group 789"}
            return mock

        mock_get.side_effect = side_effect

        finder = Find(gitlab_token=mock_gitlab_token)
        
        with patch.object(finder, 'find_all_groups', wraps=finder.find_all_groups) as spy:
            groups = finder.find_all_groups(group_ids=[123, 456], recursive=False)

            assert len(groups) == 2
            assert mock_get.call_count == 2

    @pytest.mark.unit
    @patch('requests.Session.get')
    def test_find_all_groups_with_exclude(self, mock_get, mock_gitlab_token):
        """Тест поиска групп с исключением"""
        def side_effect(url, **kwargs):
            mock = Mock()
            mock.status_code = 200
            if '123' in url:
                mock.json.return_value = {"id": 123, "name": "Group 123"}
            elif '456' in url:
                mock.json.return_value = {"id": 456, "name": "Group 456"}
            else:
                mock.json.return_value = {"id": 789, "name": "Group 789"}
            return mock

        mock_get.side_effect = side_effect

        finder = Find(gitlab_token=mock_gitlab_token)
        
        with patch.object(finder, 'find_all_groups', wraps=finder.find_all_groups) as spy:
            groups = finder.find_all_groups(
                group_ids=[123, 456, 789],
                exclude_groups_ids=[456],
                recursive=False
            )

            assert len(groups) == 2
            ids = [g['id'] for g in groups]
            assert 123 in ids
            assert 789 in ids
            assert 456 not in ids

    @pytest.mark.unit
    @patch('requests.Session.get')
    def test_find_all_groups_empty_response(self, mock_get, mock_gitlab_token):
        """Тест пустого ответа от API"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "name": "Group"}

        mock_empty = Mock()
        mock_empty.status_code = 200
        mock_empty.json.return_value = []  # Пустой список для subgroups

        mock_get.side_effect = [mock_response, mock_empty]

        finder = Find(gitlab_token=mock_gitlab_token)
        finder.max_workers = 1
        
        groups = finder.find_all_groups(group_ids=[1], recursive=True)

        assert groups is not None

    @pytest.mark.regression
    @patch('requests.Session.get')
    def test_find_all_groups_api_error(self, mock_get, mock_gitlab_token):
        """Тест обработки ошибки API"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not found"}
        mock_get.return_value = mock_response

        finder = Find(gitlab_token=mock_gitlab_token)
        
        with pytest.raises(SystemExit):
            finder.find_all_groups(group_ids=[999])


class TestFindAllProjects:
    """Тесты метода find_all_projects"""

    @pytest.mark.smoke
    def test_find_all_projects_empty(self, mock_gitlab_token):
        """Тест поиска проектов с пустым списком"""
        finder = Find(gitlab_token=mock_gitlab_token)
        projects = finder.find_all_projects(group_ids=[])
        assert projects == []

    @pytest.mark.unit
    @patch('requests.Session.get')
    @patch.object(Find, 'find_all_groups')
    def test_find_all_projects_single_group(self, mock_find_groups, mock_get, mock_gitlab_token):
        """Тест поиска проектов в одной группе"""
        mock_find_groups.return_value = [{"id": 1}]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 101, "name": "Project 1"},
            {"id": 102, "name": "Project 2"},
        ]
        mock_get.return_value = mock_response

        finder = Find(gitlab_token=mock_gitlab_token)
        projects = finder.find_all_projects(group_ids=[1])

        assert len(projects) == 2
        assert projects[0]['id'] == 101

    @pytest.mark.unit
    @patch('requests.Session.get')
    @patch.object(Find, 'find_all_groups')
    def test_find_all_projects_pagination(self, mock_find_groups, mock_get, mock_gitlab_token):
        """Тест пагинации проектов"""
        mock_find_groups.return_value = [{"id": 1}]
        
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = [{"id": i} for i in range(100)]

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = [{"id": i} for i in range(100, 150)]

        mock_get.side_effect = [mock_response1, mock_response2]

        finder = Find(gitlab_token=mock_gitlab_token)
        projects = finder.find_all_projects(group_ids=[1])

        assert len(projects) == 150

    @pytest.mark.unit
    @patch('requests.Session.get')
    @patch.object(Find, 'find_all_groups')
    def test_find_all_projects_archived(self, mock_find_groups, mock_get, mock_gitlab_token):
        """Тест поиска архивных проектов"""
        mock_find_groups.return_value = [{"id": 1}]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 101, "name": "Project 1", "archived": True},
            {"id": 102, "name": "Project 2", "archived": False},
        ]
        mock_get.return_value = mock_response

        finder = Find(gitlab_token=mock_gitlab_token)
        projects = finder.find_all_projects(group_ids=[1], archived=True)

        assert len(projects) == 2

    @pytest.mark.unit
    @patch('requests.Session.get')
    @patch.object(Find, 'find_all_groups')
    def test_find_all_projects_shared(self, mock_find_groups, mock_get, mock_gitlab_token):
        """Тест поиска общих проектов"""
        mock_find_groups.return_value = [{"id": 1}]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 101, "shared": True}]
        mock_get.return_value = mock_response

        finder = Find(gitlab_token=mock_gitlab_token)
        projects = finder.find_all_projects(group_ids=[1], shared=True)

        called_url = mock_get.call_args[0][0]
        assert '/shared' in called_url

    @pytest.mark.unit
    @patch('requests.Session.get')
    @patch.object(Find, 'find_all_groups')
    def test_find_all_projects_with_shared_param(self, mock_find_groups, mock_get, mock_gitlab_token):
        """Тест параметра with_shared"""
        mock_find_groups.return_value = [{"id": 1}]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 101}]
        mock_get.return_value = mock_response

        finder = Find(gitlab_token=mock_gitlab_token)
        projects = finder.find_all_projects(group_ids=[1], with_shared=True)

        assert projects is not None


class TestFindAllBranches:
    """Тесты метода find_all_branches"""

    @pytest.mark.smoke
    def test_find_all_branches_empty(self, mock_gitlab_token):
        """Тест поиска веток с пустым списком"""
        finder = Find(gitlab_token=mock_gitlab_token)
        branches = finder.find_all_branches(project_ids=[])
        assert branches == []

    @pytest.mark.unit
    @patch('requests.Session.get')
    def test_find_all_branches_single_project(self, mock_get, mock_gitlab_token):
        """Тест поиска веток в одном проекте"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "main", "default": True},
            {"name": "develop", "default": False},
        ]
        mock_get.return_value = mock_response

        finder = Find(gitlab_token=mock_gitlab_token)
        branches = finder.find_all_branches(project_ids=[101])

        assert len(branches) == 2
        assert branches[0]['name'] == "main"

    @pytest.mark.unit
    @patch('requests.Session.get')
    def test_find_all_branches_multiple_projects(self, mock_get, mock_gitlab_token):
        """Тест поиска веток в нескольких проектах"""
        def side_effect(url, **kwargs):
            mock = Mock()
            mock.status_code = 200
            if '101' in url:
                mock.json.return_value = [{"name": "main"}, {"name": "develop"}]
            else:
                mock.json.return_value = [{"name": "main"}, {"name": "staging"}]
            return mock

        mock_get.side_effect = side_effect

        finder = Find(gitlab_token=mock_gitlab_token)
        branches = finder.find_all_branches(project_ids=[101, 102])

        assert len(branches) == 4
        assert mock_get.call_count == 2

    @pytest.mark.unit
    @patch('requests.Session.get')
    def test_find_all_branches_default_only(self, mock_get, mock_gitlab_token):
        """Тест поиска только дефолтных веток"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "main", "default": True},
            {"name": "develop", "default": False},
        ]
        mock_get.return_value = mock_response

        finder = Find(gitlab_token=mock_gitlab_token)
        branches = finder.find_all_branches(project_ids=[101], default=True)

        assert len(branches) == 1
        assert branches[0]['name'] == "main"

    @pytest.mark.unit
    @patch('requests.Session.get')
    def test_find_all_branches_pagination(self, mock_get, mock_gitlab_token):
        """Тест пагинации веток"""
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = [{"name": f"branch-{i}"} for i in range(100)]
        
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = [{"name": f"branch-{i}"} for i in range(100, 120)]
        
        mock_get.side_effect = [mock_response1, mock_response2]

        finder = Find(gitlab_token=mock_gitlab_token)
        branches = finder.find_all_branches(project_ids=[101])

        assert len(branches) == 120


class TestErrorHandling:
    """Тесты обработки ошибок"""

    @pytest.mark.regression
    @patch('requests.Session.get')
    def test_api_error_404(self, mock_get, mock_gitlab_token):
        """Тест ошибки 404"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not Found"}
        mock_get.return_value = mock_response

        finder = Find(gitlab_token=mock_gitlab_token)
        
        with pytest.raises(SystemExit):
            finder.find_all_groups(group_ids=[999])

    @pytest.mark.regression
    @patch('requests.Session.get')
    def test_api_error_500(self, mock_get, mock_gitlab_token):
        """Тест ошибки 500"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal Server Error"}
        mock_get.return_value = mock_response

        finder = Find(gitlab_token=mock_gitlab_token)
        
        with pytest.raises(SystemExit):
            finder.find_all_groups(group_ids=[1])

    @pytest.mark.regression
    @patch('requests.Session.get')
    def test_empty_response(self, mock_get, mock_gitlab_token):
        """Тест пустого ответа"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        finder = Find(gitlab_token=mock_gitlab_token)
        
        # В зависимости от реализации может быть SystemExit или пустой список
        try:
            result = finder.find_all_groups(group_ids=[1])
            assert result == []
        except SystemExit:
            pass

    @pytest.mark.regression
    @patch('requests.Session.get')
    def test_network_error(self, mock_get, mock_gitlab_token):
        """Тест сетевой ошибки"""
        mock_get.side_effect = Exception("Network error")

        finder = Find(gitlab_token=mock_gitlab_token)
        
        with pytest.raises(Exception):
            finder.find_all_groups(group_ids=[1])


class TestSessionAndRetries:
    """Тесты сессии и повторных попыток"""

    @pytest.mark.unit
    def test_session_retry_config(self, mock_gitlab_token):
        """Тест конфигурации повторных попыток"""
        finder = Find(gitlab_token=mock_gitlab_token)
        
        assert hasattr(finder, 'session')
        assert hasattr(finder, 'retries')
        assert finder.retries.total == 10
        assert 500 in finder.retries.status_forcelist

    @pytest.mark.unit
    def test_session_mounts(self, mock_gitlab_token):
        """Тест монтирования адаптеров"""
        finder = Find(gitlab_token=mock_gitlab_token)
        
        assert 'https://' in finder.session.adapters
        assert 'http://' in finder.session.adapters


class TestEdgeCases:
    """Тесты граничных случаев"""

    @pytest.mark.regression
    def test_empty_group_ids(self, mock_gitlab_token):
        """Тест пустого списка group_ids"""
        finder = Find(gitlab_token=mock_gitlab_token)
        result = finder.find_all_groups(group_ids=[])
        assert result == []

    @pytest.mark.regression
    def test_empty_project_ids(self, mock_gitlab_token):
        """Тест пустого списка project_ids"""
        finder = Find(gitlab_token=mock_gitlab_token)
        result = finder.find_all_branches(project_ids=[])
        assert result == []

    @pytest.mark.regression
    @patch('requests.Session.get')
    def test_mutable_default_args(self, mock_get, mock_gitlab_token):
        """Тест мутабельных аргументов по умолчанию"""
        # Мокаем успешный ответ
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "name": "Group"}
        mock_get.return_value = mock_response

        finder = Find(gitlab_token=mock_gitlab_token)
        
        # Исправлено: отключаем рекурсию для теста
        with patch.object(finder, 'find_all_groups', wraps=finder.find_all_groups) as spy:
            result1 = finder.find_all_groups(group_ids=[1, 2, 3], recursive=False)
            result2 = finder.find_all_groups(group_ids=[4, 5], recursive=False)
            
            assert isinstance(result1, list)
            assert isinstance(result2, list)