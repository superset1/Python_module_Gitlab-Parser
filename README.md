# Python module Gitlab Parser

## Installation

```bash
pip install GitlabParser
```

## Usage

```
from GitlabParser import Find

finder = Find(gitlab_token="your_token")
groups = finder.find_all_groups(group_ids=[1, 2, 3])
```
