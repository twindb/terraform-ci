"""Module runs a job in Travis-CI."""
import logging
import sys
from os import environ, path as osp, EX_SOFTWARE
import click

from terraform_ci import DEFAULT_TERRAFORM_VARS, setup_environment, run_job, \
    render_comment, module_name_from_path, convert_to_newlines
from terraform_ci.post_plan import post_comment

LOG = logging.getLogger(__name__)


@click.command()
@click.option(
    '--modules-path',
    default='./',
    help='Path to directory with Terraform modules',
    show_default=True,
)
@click.option(
    '--env-file',
    help='A JSON file with terraform environment variables',
    default=DEFAULT_TERRAFORM_VARS,
    show_default=True,
)
@click.argument(
    'action',
    type=click.Choice(['plan', 'apply'])
)
def terraform_ci(modules_path, env_file, action):
    """
    Run Terraform action.

    The tool prepares environment, sets environment variables for
    API keys, passwords etc.

    It then runs a terraform action which may be either plan or apply.

    ci-runner can be called in a CI environment or locally on
    a workstation.
    """
    logging.basicConfig(level=logging.DEBUG)

    try:
        pull_request = not environ['TRAVIS_PULL_REQUEST'] == "false"

    except KeyError:
        pull_request = False

    try:
        setup_environment(env_file)

    except FileNotFoundError:
        LOG.warning("Environment file %s doesn't exit", env_file)

    # module name is parent directory
    mod = module_name_from_path(modules_path)
    LOG.info('Processing module %s', mod)

    status = {
        mod: run_job(
            osp.join(modules_path),
            action
        )
    }

    if status[mod]['success']:
        LOG.info('%s success: %s', mod, status[mod]['success'])
    else:
        LOG.error(
            'Failed to process %s: %s',
            mod,
            status[mod]['stderr'].decode('utf-8')
        )
        exit(EX_SOFTWARE)

    if pull_request:
        post_comment(
            comment=render_comment(status)
        )
    else:
        LOG.info('Standard output:')
        sys.stdout.write(
            convert_to_newlines(
                status[mod]['stdout']
            ) or 'no output\n'
        )
        LOG.info('Standard error output:')
        sys.stderr.write(
            convert_to_newlines(
                status[mod]['stderr']
            ) or 'no output\n'
        )
