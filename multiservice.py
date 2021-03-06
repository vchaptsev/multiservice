"""Multiservice is a tool to affect multiple repositories simultaneously"""

__version__ = '1.7.0'


import os
import subprocess
from typing import Any, Dict, List, Optional

import typer
import yaml
from rich import print

REQUIRED_KEYS = ['root', 'services', 'commands']
WRAPPER = 'pushd {PATH} > /dev/null && {COMMAND} && popd > /dev/null'

app = typer.Typer()


def validate_config(config: Dict[str, Any]) -> None:
    missing_keys = [key for key in REQUIRED_KEYS if key not in config]
    if missing_keys:
        raise typer.BadParameter(f'Config misses required keys: {missing_keys}')


def parse_config(path: str) -> Dict[str, Any]:
    full_path = os.path.expanduser(path)

    with open(full_path) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    validate_config(config)
    return config


def run(command: str) -> None:
    subprocess.call(command, shell=True, executable=os.environ.get('SHELL', '/bin/sh'))


def get_command_from_config(command: str, config: Dict[str, Any]) -> str:
    if command not in config['commands']:
        raise typer.BadParameter(f'Unknown command: "{command}"')

    command_from_config = config['commands'][command].strip()
    return command_from_config


def wrap_command_in_template(command: str, config: Dict[str, Any]) -> str:
    return config['template'].strip().format(COMMAND=command)


def execute_for_services(command: str, code: str, services: List[str], config: Dict[str, Any]) -> None:
    for service in services:
        if service in config['services']:
            service_dir = config['services'][service]
        elif service.upper() in config['services']:
            service_dir = config['services'][service.upper()]
        else:
            raise typer.BadParameter(f'Service {service} not found')

        print(  # noqa: T001
            '[bold cyan]Running[/bold cyan] '
            f'[bold magenta]{command}[bold magenta] '
            '[bold cyan]for:[/bold cyan] '
            f'[bold green]{service_dir}[/bold green]',
        )

        path = os.path.join(config['root'], service_dir)
        wrapped_command = WRAPPER.format(PATH=path, COMMAND=code).format(SERVICE=service_dir)

        run(wrapped_command)

        print('\n')  # noqa: T001


@app.command()
def multiservice(
    config_path: str = typer.Option('~/.multiservice.yml', '--config', '-c'),  # noqa
    custom_command: str = typer.Option('', '--execute', '-e'),  # noqa
    command: str = typer.Argument(...),  # noqa
    services: Optional[List[str]] = typer.Argument(None),  # noqa
) -> None:
    config = parse_config(config_path)

    if command == 'edit':
        editor = config.get('editor')
        if not editor:
            raise typer.BadParameter('Please set "editor" in the config')
        return run(f'{editor} {config_path}')

    elif command == 'execute':
        code = custom_command

    else:
        code = get_command_from_config(command=command, config=config)

    services = services or list(config['services'])
    code = wrap_command_in_template(command=code, config=config)
    execute_for_services(command=command, code=code, services=services, config=config)


if __name__ == '__main__':
    app()
