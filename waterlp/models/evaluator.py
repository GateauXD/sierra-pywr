from os import environ
import json
from calendar import isleap
import pandas


def eval_scalar(x):
    try:  # create the function
        if type(x) == str and len(x):
            x = float(x)
        else:
            x = None
    except ValueError as err:  # value error
        errormsg = "\"{}\" is not a number".format(x)
        raise Exception(errormsg)

    return x


def eval_descriptor(s):
    return s


def eval_timeseries(timeseries, dates, fill_value=None, fill_method=None, flatten=False, flavor=None,
                    date_format='%Y-%m-%d %H:%M:%S'):
    try:

        df = pandas.read_json(timeseries)
        if df.empty:
            df = pandas.DataFrame(index=dates, columns=['0'])
        else:
            # TODO: determine if the following reindexing is needed; it's unclear why it was added
            # this doesn't work with periodic timeseries, as Pandas doesn't like the year 9999
            # df = df.reindex(pandas.DatetimeIndex(dates))
            if fill_value is not None:
                df.fillna(value=fill_value, inplace=True)
            elif fill_method:
                df.fillna(method=fill_method)

        if flatten:
            df = df.sum(axis=1)

        if flavor == 'pandas':
            result = df
        elif flavor == 'native':
            df.index = pandas.DatetimeIndex(dates).strftime(date_format=date_format)
            result = df.to_dict()
        elif flavor == 'json':
            result = df.to_json(date_format='iso')
        else:
            result = df.to_json(date_format='iso')

    except:
        raise Exception('Error parsing timeseries data')

    return result


def eval_array(array, flavor=None):
    result = None
    try:
        array_as_list = json.loads(array)
        if flavor is None:
            result = array
        elif flavor == 'native':
            result = array_as_list
        elif flavor == 'pandas':
            result = pandas.DataFrame(array_as_list)
        return result
    except:
        errormsg = 'Something is wrong.'
        raise Exception(errormsg)


def parse_function(user_code, name, argnames, modules=()):
    """Parse a function into usable Python"""

    # first, parse code
    spaces = '\n    '
    s = user_code.rstrip()
    lines = s.split('\n')
    if 'return ' not in lines[-1]:
        lines[-1] = 'return ' + lines[-1]
    code = spaces.join(lines)

    try:
        eval1 = eval(user_code)
        eval2 = eval(user_code)
        if user_code and eval1 == eval2:
            return '''def {name}(self):{spaces}{code}'''.format(spaces=spaces, code=code, name=name)
    except:
        pass

    # modules
    # modules = spaces.join('import {}'.format(m) for m in modules if m in user_code)

    # getargs (these pass to self.GET)
    kwargs = spaces.join(['{arg} = kwargs.get("{arg}")'.format(arg=arg) for arg in argnames if arg in user_code])

    # final function
    func = '''def {name}(self, **kwargs):{spaces}{spaces}{kwargs}{spaces}{code}''' \
        .format(spaces=spaces, kwargs=kwargs, code=code, name=name)

    return func


def eval_function(function, data_type):
    if function is None or type(function) != str:
        return ''

    if data_type == 'descriptor':
        return function

    try:
        return eval(function)
    except:
        return function


class Timestep(object):
    index = -1
    periodic_timestep = 1

    def __init__(self, date, start_date, span):
        if date == start_date:
            type(self).index = 0
            type(self).periodic_timestep = 1
        else:
            type(self).index += 1
        self.index = type(self).index
        self.timestep = self.index + 1
        self.date = date
        self.year = date.year
        self.month = date.month
        self.day = date.day
        self.date_as_string = date.isoformat(' ')

        if start_date:
            if date.month < start_date.month:
                self.water_year = date.year
            else:
                self.water_year = date.year + 1

        if span:
            self.span = span
            self.set_periodic_timestep(date, start_date, span)

    def set_periodic_timestep(self, date, start_date, span):

        if span == 'day':
            if (date.month, date.day) == (start_date.month, start_date.day):
                type(self).periodic_timestep = 1
            else:
                type(self).periodic_timestep += 1
            self.periodic_timestep = type(self).periodic_timestep

        elif span == 'week':
            self.periodic_timestep = self.index % 52 + 1

        elif span == 'month':
            self.periodic_timestep = self.index % 12 + 1

        elif span == 'thricemonthly':
            self.periodic_timestep = self.index % 36 + 1


def make_timesteps(data_type='timeseries', **kwargs):
    # TODO: Make this more advanced

    span = kwargs.get('span') or kwargs.get('timestep') or kwargs.get('time_step')
    start = kwargs.get('start') or kwargs.get('start_time')
    end = kwargs.get('end') or kwargs.get('end_time')

    timesteps = []

    if start and end and span:
        start_date = pandas.to_datetime(start)
        end_date = pandas.to_datetime(end)
        span = span.lower()

        if data_type == 'periodic timeseries':
            start_date = pandas.datetime(9998, 1, 1)
            end_date = pandas.datetime(9998, 12, 31, 23, 59)

        if span == 'day':
            timesteps = [Timestep(d, start_date, span) for d in pandas.date_range(start=start, end=end, freq='D')]
        elif span == 'week':
            dates = []
            for i in range(52 * (end_date.year - start_date.year)):
                if i == 0:
                    date = start_date
                else:
                    date = dates[-1] + pandas.DateOffset(days=7)
                if isleap(date.year) and date.month == 3 and date.day == 4:
                    date += pandas.DateOffset(days=1)
                if date.month == 12 and date.day == 31:
                    date += pandas.DateOffset(days=1)
                dates.append(date)
            timesteps = [Timestep(date, start_date, 'week') for date in dates]
        elif span == 'month':
            timesteps = [Timestep(d, start_date, 'month') for d in pandas.date_range(start=start, end=end, freq='M')]
        elif span == 'thricemonthly':
            dates = []
            for date in pandas.date_range(start=start, end=end, freq='M'):
                d1 = pandas.datetime(date.year, date.month, 10)
                d2 = pandas.datetime(date.year, date.month, 20)
                d3 = pandas.datetime(date.year, date.month, date.daysinmonth)
                dates.extend([d1, d2, d3])
            timesteps = [Timestep(d, start_date, span) for d in dates]

    return timesteps


class InnerSyntaxError(SyntaxError):
    """Exception for syntax errors that will be defined only where the SyntaxError is made.

    Attributes:
        expression -- input expression in which the error occurred
        message    -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class EvalException(Exception):
    def __init__(self, message, code):
        self.message = message
        self.code = code


class Evaluator:
    def __init__(self, conn=None, scenario_id=None, data_type='timeseries', nblocks=1, files_path=None,
                 time_settings=None, date_format='%Y-%m-%d %H:%M:%S', **kwargs):
        self.conn = conn

        self.dates = []
        self.dates_as_string = []
        self.timesteps = []
        self.start_date = None
        self.end_date = None

        if data_type in [None, 'timeseries', 'periodic timeseries']:
            self.timesteps = make_timesteps(data_type=data_type, **time_settings)
            debug_start = kwargs.pop('debug_start', None)
            debug_ts = kwargs.pop('debug_ts', None)
            if debug_start:
                debug_start = pandas.Timestamp(debug_start)
                self.timesteps = [t for t in self.timesteps if t.date >= debug_start]
            self.timesteps = self.timesteps[:debug_ts]
            self.dates = [t.date for t in self.timesteps]
            self.dates_as_string = [t.date_as_string for t in self.timesteps]
            self.start_date = self.dates[0].date
            self.end_date = self.dates[-1].date

        self.date_format = date_format
        self.tsi = None
        self.tsf = None
        self.scenario_id = scenario_id
        self.data_type = data_type
        self.default_timeseries = None
        self.resource_scenarios = {}

        self.external = {}

        self.bucket_name = environ.get('AWS_S3_BUCKET')
        self.files_path = files_path

    def eval_data(self, value, func=None, flavor=None, depth=0, flatten=False, fill_value=None,
                  tsidx=None, date_format=None, data_type=None):
        """
        Evaluate the data and return the appropriate value

        :param value:
        :param func:
        :param flavor:
        :param depth:
        :param flatten:
        :param fill_value:
        :param date_format:
        :param data_type:
        :return:
        """

        result = None
        date_format = date_format or self.date_format

        # metadata = json.loads(resource_scenario.value.metadata)
        metadata = json.loads(value.metadata)
        if func is None:
            func = metadata.get('function')
        use_function = metadata.get('use_function', 'N') == 'Y' or metadata.get('input_method') == 'function'
        data_type = data_type or value.type

        if use_function:
            return eval_function(func, data_type)

        elif data_type == 'scalar':
            try:
                return eval_scalar(value.value)
            except Exception as err:
                raise

        elif data_type == 'descriptor':
            try:
                return eval_descriptor(value.value)

            except Exception as err:
                raise

        elif data_type in ['timeseries', 'periodic timeseries']:
            try:
                return eval_timeseries(
                    value.value,
                    self.dates_as_string,
                    date_format=date_format,
                    fill_value=fill_value,
                    flavor=flavor,
                )

            except Exception as err:
                raise

        elif data_type == 'array':
            try:
                return eval_array(
                    value.value,
                    flavor=flavor
                )
            except Exception as err:
                raise
