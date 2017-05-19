#!/usr/bin/env python

import argparse
import logging as log
import re
import time
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

import yaml
from bioblend.galaxy import GalaxyInstance

from .common_parser import get_common_args

DEFAULT_URL = "http://localhost"


def wait(gi, job):
    """
        Waits until a data_manager is finished or failed.
        It will check the state of the created datasets every 30s.
    """
    while True:
        value = job['outputs']
        # check if the output of the running job is either in 'ok' or 'error' state
        if gi.datasets.show_dataset(value[0]['id'])['state'] in ['ok', 'error']:
            break
        log.info('Data manager still running.')
        time.sleep(30)


def run_dm(args):
    url = args.galaxy or DEFAULT_URL
    if args.api_key:
        gi = GalaxyInstance(url=url, key=args.api_key)
    else:
        gi = GalaxyInstance(url=url, email=args.user, password=args.password)
    # should test valid connection
    # The following should throw a ConnectionError when invalid API key or password
    genomes = gi.genomes.get_genomes()
    log.info('Number of installed genomes: %s' % str(len(genomes)) )

    conf = yaml.load(open(args.config))
    for dm in conf.get('data_managers'):
        for item in dm.get('items', [None]):
            dm_id = dm['id']
            params = dm['params']
            log.info('Running DM: %s' % dm_id)
            inputs = dict()
            # Iterate over all parameters, replace occurences of {{item}} with the current processing item
            # and create the tool_inputs dict for running the data manager job
            for param in params:
                key, value = param.items()[0]
                value = re.sub(r'{{\s*item\s*}}', item, value, flags=re.IGNORECASE)
                inputs.update({key: value})

            # run the DM-job
            job = gi.tools.run_tool(history_id=None, tool_id=dm_id, tool_inputs=inputs)
            wait(gi, job)
            log.info('Reloading data managers table.')
            for data_table in dm.get('data_table_reload', []):
                # reload two times
                for i in range(2):
                    gi.make_get_request(urljoin(url, 'api/tool_data/%s/reload' % data_table))
                    time.sleep(5)


def main():

    parent = get_common_args()

    parser = argparse.ArgumentParser(
        parents=[parent],
        description='Running Galaxy data managers in a defined order with defined parameters.')
    parser.add_argument("--config", required=True, help="Path to the YAML config file with the list of data managers and data to install.")

    args = parser.parse_args()
    if args.verbose:
        log.basicConfig(level=log.DEBUG)

    log.info("Running data managers...")
    run_dm(args)


if __name__ == '__main__':
    main()
