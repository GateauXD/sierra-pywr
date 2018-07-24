import argparse
from ast import literal_eval
import multiprocessing as mp
import os
import sys
import uuid
from datetime import datetime
from functools import partial
from itertools import product

from connection import connection
from system_class import WaterSystem
from scenario_class import Scenario
from post_reporter import Reporter as PostReporter

from logger import create_logger
from utils import create_subscenarios

from copy import copy

from scenario_main import run_scenario


def run_scenarios(args, log):
    """
        This is a wrapper for running all the scenarios, where scenario runs are
        processor-independent. As much of the Pyomo model is created here as
        possible.
    """

    verbose = False

    # from scenario_debug import run_scenario
    print('')
    if args.debug:
        # from scenario_debug import run_scenario
        print("DEBUG ON")
    else:
        # scenario is the Cythonized version of scenario_main
        print("DEBUG OFF")

    args.starttime = datetime.now()  # args.start_time is iso-formatted, but this is still probably redundant

    print("================================================")
    print("STARTING RUN")
    print("Start time: {}".format(args.starttime.isoformat()))
    print("================================================")

    # ======================
    # connect to data server
    # ======================
    all_scenario_ids = list(set(sum(args.scenario_ids, ())))
    conn = connection(args=args, scenario_ids=all_scenario_ids)

    # ====================================
    # define subscenarios (aka variations)
    # ====================================

    # create a dictionary of network attributes
    network = conn.call('get_network', {'network_id': conn.network.id, 'include_data': 'N', 'summary': 'N',
                                        'include_resources': 'N'})
    template_attributes = conn.call('get_template_attributes', {'template_id': conn.template.id})
    attrs = {ta.id: {'name': ta.name} for ta in template_attributes}

    # create the system
    base_system = WaterSystem(
        conn=conn,
        name=args.app_name,
        all_scenarios=network.scenarios,
        network=conn.network,
        template=conn.template,
        # date_format=args.hydra_timestep_format,
        date_format='%Y-%m-%d %H:%M:%S',
        args=args,
    )

    scenario_lookup = {}

    all_supersubscenarios = []

    # prepare the reporter
    if args.message_protocol is not None:
        post_reporter = PostReporter(args)
    else:
        post_reporter = None

    for scenario_ids in args.scenario_ids:

        try:
            scenario_ids = list(scenario_ids)
        except:
            scenario_ids = [scenario_ids]

        # create the scenario class
        scenario = Scenario(scenario_ids=scenario_ids, conn=conn, network=conn.network, args=args)

        start_payload = scenario.update_payload(action='start')
        post_reporter.start(is_main_reporter=(args.message_protocol == 'post'),
                            **start_payload)  # kick off reporter with heartbeat

        # create the system class
        # TODO: pass resources as dictionaries instead for quicker lookup
        option_subscenarios = create_subscenarios(conn.network, conn.template, scenario.option, 'option')
        scenario_subscenarios = create_subscenarios(conn.network, conn.template, scenario.scenario, 'scenario')

        try:

            # prepare the system
            system = copy(base_system)
            system.scenario = scenario
            system.initialize_time_steps()
            system.collect_source_data()

            # organize the subscenarios
            flattened = product(option_subscenarios, scenario_subscenarios)
            subscenario_count = len(option_subscenarios) * len(scenario_subscenarios)

            if args.debug:
                verbose = True
                system.nruns = min(args.debug_ts, system.nruns)
                system.dates = system.dates[:system.nruns]
                system.dates_as_string = system.dates_as_string[:system.nruns]

                subscenario_count = min(subscenario_count, 1)

            system.scenario.subscenario_count = subscenario_count
            system.scenario.total_steps = subscenario_count * len(system.dates)

            supersubscenarios = [{
                'i': i + 1,
                'system': copy(system),  # this is intended to be a shallow copy
                'variation_sets': variation_sets,
            } for i, variation_sets in enumerate(flattened)]

            all_supersubscenarios.extend(supersubscenarios[:subscenario_count])

        except Exception as err:
            err_class = err.__class__.__name__
            if err_class == 'InnerSyntaxError':
                m = err.message
            else:
                m = "Unknown error."
            message = "Failed to prepare system. Error: {}".format(m)

            post_reporter.report(action="error", message=message)

            raise

    # =======================
    # multiprocessing routine
    # =======================

    if args.debug:
        run_scenario(all_supersubscenarios[0], args=args)
        return
    else:
        p = partial(run_scenario, args=args, verbose=verbose)

        # set multiprocessing parameters
        poolsize = mp.cpu_count()
        maxtasks = None
        chunksize = 1
        pool = mp.Pool(processes=poolsize, maxtasksperchild=maxtasks)

        msg = 'Running {} subscenarios in multicore mode with {} workers, {} chunks each.' \
            .format(system.scenario.subscenario_count, poolsize, chunksize)
        print(msg)

        pool.imap(p, all_supersubscenarios, chunksize=chunksize)
        pool.close()
        pool.join()
        return


def commandline_parser():
    """
        Parse the arguments passed in from the command line.
    """
    parser = argparse.ArgumentParser(
        description="""A water system optimization model framework for OpenAgua.
                    Written by David Rheinheimer <drheinheimer@itesm.mx>
                    (c) Copyright 2016, Tecnologico de Monterrey.
        """, epilog="For more information visit www.openagua.org",
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--app', dest='app_name', help='''Name of the app.''')
    parser.add_argument('--durl', dest='data_url', help='''The Hydra Server URL.''')
    parser.add_argument('--user', dest='hydra_username', help='''The username for logging in to Hydra Server.''')
    parser.add_argument('--pw', dest='hydra_password',
                        help='''The password for logging in to Hydra Server.''')
    parser.add_argument('--sid', dest='session_id',
                        help='''The Hydra Server session ID.''')
    parser.add_argument('--uid', dest='user_id', type=int,
                        help='''The Hydra Server user_id.''')
    parser.add_argument('--src', dest='source_id', type=int,
                        help='''The source ID of the model to be run.''')
    parser.add_argument('--nid', dest='network_id', type=int,
                        help='''The network ID of the model to be run.''')
    parser.add_argument('--tid', dest='template_id', type=int,
                        help='''The template ID of the model to be run.''')
    parser.add_argument('--scids', dest='scenario_ids',
                        help='''The IDs of the scenarios to be run,
                        specified as a string containing a comma-separated list of
                        integers or integer tuples.
                        ''')
    parser.add_argument('--htsf', dest='hydra_timestep_format',
                        help='''The format of a time step in Hydra Platform (found in hydra.ini).''')
    parser.add_argument('--ldir', dest='log_dir',
                        help='''The main log file directory.''')
    parser.add_argument('--sol', dest='solver', default='glpk',
                        help='''The solver to use (e.g., glpk, gurobi, etc.).''')
    parser.add_argument('--fs', dest='foresight', default='zero', help='''Foresight: 'perfect' or 'imperfect' ''')
    parser.add_argument('--purl', dest='post_url',
                        help='''URL to ping indicating activity.''')
    parser.add_argument('--mp', dest='message_protocol', default=None,
                        help='''Message protocol to report progress back to client browser''')
    parser.add_argument('--wurl', dest='websocket_url',
                        help='''URL and port that is listening for activity.''')
    parser.add_argument('--guid', default=uuid.uuid4().hex, dest='unique_id',
                        help='''Unique identifier for this run.''')
    parser.add_argument('--debug', dest='debug', action='store_true', help='''Debug flag.''')
    parser.add_argument('--debug_ts', dest='debug_ts', type=int, default=10,
                        help='''The number of timesteps to run in debug mode.''')
    parser.add_argument('--debug_gain', dest='debug_gain', action='store_true', help='''Debug flag for the Pyomo model.''')
    parser.add_argument('--debug_loss', dest='debug_loss', action='store_true', help='''Debug flag for the Pyomo model.''')
    parser.add_argument('--c', dest='custom', type=dict, default={},
                        help='''Custom arguments passed as stringified JSON.''')
    parser.add_argument('--dest', dest='destination', default='source',
                        help='''Destination of results. Options for now include "source" or "aws_s3"''')
    parser.add_argument('--si', dest='suppress_input', action='store_true',
                        help='''Suppress input from results. This can speed up writing results.''')
    parser.add_argument('--st', dest='start_time', default=datetime.now().isoformat(), help='''Run start time.''')
    parser.add_argument('--rkey', dest='report_api_key', default='',
                        help='''Generic option for passing an API key for reporting to client.''')

    return parser


args = {}


def main():
    global args
    parser = commandline_parser()
    args, unknown = parser.parse_known_args(sys.argv[1:])
    here = os.path.abspath(os.path.dirname(__file__))

    # log file location - based on user

    # initialize log directories
    args.log_dir = os.path.join(here, 'logs', args.log_dir)

    # specify scenarios log dir
    args.scenario_log_dir = 'scenario_logs'
    args.scenario_log_dir = os.path.join(args.log_dir, args.scenario_log_dir)

    if not os.path.exists(args.log_dir):
        os.makedirs(args.scenario_log_dir)

    # create top-level log file
    logfile = os.path.join(args.log_dir, 'log.txt')
    log = create_logger(args.app_name, logfile, '%(asctime)s - %(message)s')

    # pre-processing
    if args.scenario_ids:
        args.scenario_ids = literal_eval(args.scenario_ids)

    argdict = args.__dict__.copy()
    argtuples = sorted(argdict.items())
    args_str = '\n\t'.join([''] + ['{}: {}'.format(a[0], a[1]) for a in argtuples])
    log.info('started model run with args: %s' % args_str)

    run_scenarios(args, log)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
