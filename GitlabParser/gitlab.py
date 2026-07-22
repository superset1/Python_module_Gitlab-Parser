import requests
import os
import concurrent.futures
from requests.adapters import HTTPAdapter
from typing import Optional
from urllib3.util.retry import Retry
from cozy_logger import Logger

class Find:
    '''Recursive parsing Gitlab'''

    gitlab_url = 'https://gitlab.com'
    gitlab_token = os.getenv('GITLAB_TOKEN_WRITE', '')
    max_workers = (os.cpu_count() or 1) * 10

    session = requests.Session()
    retries = Retry(total=10,
                    backoff_factor=0.1,
                    status_forcelist=[409, 500, 502, 503, 504],
                    allowed_methods=frozenset(['GET', 'POST']))
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    def __init__(self, gitlab_url: str=gitlab_url, gitlab_token: str=gitlab_token, max_workers: int=max_workers):
        self.gitlab_url = gitlab_url
        self.gitlab_token = gitlab_token
        self.headers = {'PRIVATE-TOKEN': gitlab_token}
        self.logger = Logger.get_current_logger() or Logger().get_logger()
        self.max_workers = max_workers

    def find_all_groups(self, *, group_ids: list=[], exclude_groups_ids: list=[], with_projects: bool=True, recursive: bool=True) -> list:
        """Recursive search all groups.

        Args:
            List of group IDs to retrieve.
                Defaults to [].
            exclude_groups_ids (list, optional): Group IDs to exclude from results.
                Defaults to [].
            with_projects (bool, optional): If True, includes project data for each group.
                If False, returns only group metadata (faster). Defaults to True.
            recursive (bool, optional): If True, recursive search of all subgroups.
                If False, only returns direct children. Defaults to True.

        Returns:
            list: List of group objects matching the search criteria.

        Examples:
            >>> find_all_groups()
            [<Group 1>, <Group 2>, ...]

            >>> find_all_groups(group_ids=[1, 2], with_projects=False)
            [<Group 1>, <Group 2>]

            >>> find_all_groups(exclude_groups_ids=[5, 10], recursive=False)
            [<Group 1>, <Group 2>, ...]
        """

        groups = []
        group_ids = [group_id for group_id in group_ids if group_id not in exclude_groups_ids]

        def get_groups_info(group_id):
            url = f"{self.gitlab_url}/api/v4/groups/{group_id}"
            params = {
                "with_projects": with_projects
            }
            response = self.session.get(url, headers=self.headers, params=params)

            if response.status_code != 200:
                self.logger.critical(f'Cannot get info for group id {group_id}. Status code is {response.status_code}.')
                exit(1)

            group_data = response.json()
            if len(group_data) == 0:
                self.logger.critical(f'Empty data for group id {group_id}.')
                exit(1)

            if group_data['id'] not in exclude_groups_ids:
                groups.append(group_data)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for result in executor.map(get_groups_info, group_ids):
                if result:
                    self.logger.info(result)

        if recursive:
            def get_subgroups_info_recursive(group_id):
                page = 1
                while True:
                    url = f"{self.gitlab_url}/api/v4/groups/{group_id}/subgroups"
                    params = {
                        "with_projects": with_projects,
                        "per_page": 100,
                        "page": page
                    }
                    response = self.session.get(url, headers=self.headers, params=params)

                    if response.status_code != 200:
                        self.logger.critical(f'Cannot get subgroups info for group id {group_id}. Status code is {response.status_code}.')
                        exit(1)

                    subgroups_data = response.json()
                    if len(subgroups_data) == 0:
                        break

                    groups.extend([subgroup for subgroup in subgroups_data if subgroup['id'] not in exclude_groups_ids])
                    subgroups_ids_temp = [subgroup['id'] for subgroup in subgroups_data if subgroup['id'] not in exclude_groups_ids]

                    with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                        for result in executor.map(get_subgroups_info_recursive, subgroups_ids_temp):
                            if result:
                                self.logger.info(result)

                    if len(subgroups_data) < 100:
                        break

                    page += 1

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                for result in executor.map(get_subgroups_info_recursive, group_ids):
                    if result:
                        self.logger.info(result)

        return groups

    def find_all_projects(self, *, group_ids: list=[], project_ids: list=[], exclude_groups_ids: list=[], exclude_project_ids: list=[], recursive: bool=True, archived: Optional[bool] = None, with_shared: bool=False, shared: bool=False) -> list:
        """Recursive search all projects in groups or specific projects.

        Args:
            group_ids (list, optional): List of group IDs to search in.
                Defaults to empty list.
            project_ids (list, optional): List of specific project IDs to fetch.
                Defaults to empty list.
            exclude_groups_ids (list, optional): Group IDs to exclude from search.
                Defaults to empty list.
            exclude_project_ids (list, optional): Project IDs to exclude from results.
                Defaults to empty list.
            recursive (bool, optional): If True, recursive search of all projects in subgroups.
                Defaults to True.
            archived (Optional[bool], optional): Filter by archived status.
                If None, returns both archived and non-archived projects.
                Defaults to None.
            with_shared (bool, optional): If True, include shared projects from other groups.
                Defaults to False.
            shared (bool, optional): If True, return only shared projects.
                Defaults to False.

        Returns:
            list: List of project objects matching the search criteria.

        Examples:
            >>> find_all_projects(group_ids=[1, 2], recursive=True)
            [<Project 1>, <Project 2>, ...]

            >>> find_all_projects(project_ids=[1, 2])
            [<Project 1>, <Project 2>, ...]
        """

        projects = []

        if recursive and group_ids:
            group_ids = [group_data['id'] for group_data in self.find_all_groups(group_ids=group_ids, exclude_groups_ids=exclude_groups_ids)]

        def find_projects_in_group(group_id):
            page = 1
            while True:
                url = f"{self.gitlab_url}/api/v4/groups/{group_id}/projects{'/shared' if shared else ''}"
                params = {
                  "include_subgroups": False,
                  "archived": archived,
                  "with_shared": with_shared,
                  "per_page": 100,
                  "page": page
                }
                response = self.session.get(url, headers=self.headers, params=params)

                if response.status_code != 200:
                    self.logger.critical(f'Cannot get projects in group id {group_id}. Status code is {response.status_code}.')
                    exit(1)

                projects_data = response.json()
                if len(projects_data) == 0:
                    break

                projects.extend([project for project in projects_data if project['id'] not in exclude_project_ids])

                if len(projects_data) < 100:
                    break

                page += 1

        def find_project(project_id):
            url = f"{self.gitlab_url}/api/v4/projects/{project_id}"
            response = self.session.get(url, headers=self.headers)

            if response.status_code != 200:
                self.logger.critical(f'Cannot get project id {project_id}. Status code is {response.status_code}.')
                exit(1)

            projects_data = response.json()
            if len(projects_data) == 0:
                return

            if archived is None or archived == projects_data.get('archived'):
                projects.append(projects_data)

        if group_ids:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                for result in executor.map(find_projects_in_group, group_ids):
                    if result:
                        self.logger.info(result)

        found_project_ids = [project['id'] for project in projects]
        project_ids = [project_id for project_id in project_ids if project_id not in exclude_project_ids and project_id not in found_project_ids]

        if project_ids:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                for result in executor.map(find_project, project_ids):
                    if result:
                        self.logger.info(result)

        return projects

    def find_all_branches(self, *, project_ids: list=[], default: bool=False) -> list:
        '''Search all branches in projects'''
        branches = []

        def find_branches_in_project(project_id):
            page = 1
            while True:
                url = f"{self.gitlab_url}/api/v4/projects/{project_id}/repository/branches"
                params = {
                  "per_page": 100,
                  "page": page
                }
                response = self.session.get(url, headers=self.headers, params=params)

                if response.status_code != 200:
                    self.logger.critical(f'Cannot get branches in project id {project_id}. Status code is {response.status_code}.')
                    exit(1)

                branches_data = response.json()
                if len(branches_data) == 0:
                    break

                branches.extend(branches_data)

                if len(branches_data) < 100:
                    break

                page += 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for result in executor.map(find_branches_in_project, project_ids):
                if result:
                    self.logger.info(result)

        if default:
            default_branch = [branch for branch in branches if branch.get('default')]
            return default_branch

        return branches
