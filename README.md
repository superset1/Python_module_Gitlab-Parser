# Python module Gitlab Parser

## Installation

```bash
pip install GitlabParser
```

## Usage

```
from GitlabParser import Logger, Find

Logger = Logger()
logger = Logger.get_logger()
if Logger.LOG_FILE:
    print(f"See log here: {Logger.LOG_FILE}")

finder = Find(gitlab_token="your_token")
groups = finder.find_all_groups(group_ids=[1, 2, 3])
```
