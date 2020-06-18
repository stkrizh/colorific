import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
DEFAULT_CONFIG = BASE_DIR / "config.yaml"


@dataclass(frozen=True)
class Config:
    postgres: "PostgresConfig"
    colorific: "ColorificConfig"


@dataclass(frozen=True)
class PostgresConfig:
    database: str
    user: str
    password: str
    host: str
    port: str

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


@dataclass(frozen=True)
class ColorificConfig:
    pool_exec_size: int


def setup(section: str) -> None:
    global config
    config = parse_config(section)


def parse_config(
    section: str = "default", path: Path = DEFAULT_CONFIG, tag: str = "!ENV"
) -> Config:
    """
    Load yaml configuration file and resolve any environment variables.
    The environment variables must have !ENV before them and be in this format
    to be parsed: ${VAR_NAME}.

    For example:
    var: !ENV ${ENV_VAR}
    """
    # pattern for global vars: look for ${word}
    pattern = re.compile(r".*?\${(\w+)}.*?")
    loader = yaml.SafeLoader

    # the tag will be used to mark where to start searching for the pattern
    # e.g. somekey: !ENV somestring${MYENVVAR}blah blah blah
    loader.add_implicit_resolver(tag, pattern, None)
    loader.add_constructor(tag, _constructor_env_variables(pattern))

    load_dotenv()
    with open(path) as conf_data:
        data = yaml.load(conf_data, Loader=loader)

    config = data["default"]

    if section != "default":
        _merge_config_sections(config, data[section])

    return Config(
        postgres=PostgresConfig(**config["postgres"]),
        colorific=ColorificConfig(**config["colorific"]),
    )


def _constructor_env_variables(pattern: re.Pattern):
    """
    Extracts the environment variable from the node's value.
    """

    def inner(loader: yaml.Loader, node):
        value = loader.construct_scalar(node)
        for env_name in pattern.findall(value):
            env = os.environ.get(env_name)
            if not env:
                return None
            value = value.replace(f"${{{env_name}}}", env)
        return value

    return inner


def _merge_config_sections(base: dict, child: dict) -> None:
    for key, value in child.items():
        if key not in base:
            base[key] = value
        elif isinstance(value, dict):
            _merge_config_sections(base[key], value)
        else:
            base[key] = value


def __getattr__(key: str):
    return getattr(config, key)


config = parse_config()
