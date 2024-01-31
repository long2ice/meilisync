import os
import re

import yaml


class EnvVarLoader(yaml.SafeLoader):
    pass


def path_constructor(loader, node):
    return os.path.expandvars(node.value)


path_matcher = re.compile(r".*\$\{([^}^{]+)\}.*")
# apply path_constructor to YAML nodes that match the ${...} expression pattern
EnvVarLoader.add_implicit_resolver("!path", path_matcher, None)
EnvVarLoader.add_constructor("!path", path_constructor)


def parse_yaml(config_file: str) -> dict:
    with open(config_file) as f:
        config = yaml.load(f, Loader=EnvVarLoader)

    return config
