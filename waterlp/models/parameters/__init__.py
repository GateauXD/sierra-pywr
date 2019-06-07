import os
import pandas as pd

from pywr.parameters import Parameter
from .converter import convert


class WaterLPParameter(Parameter):
    store = {}  # TODO: create h5 store on disk (or redis?) to share between class instances
    root_path = os.environ.get('WATERLP_ROOT_PATH', '')

    # def convert(self, *args, **kwargs):
    #     return convert(*args, **kwargs)

    def read_csv(self, *args, **kwargs):
        hashval = hash(str(args) + str(kwargs))

        data = self.store.get(hashval)

        if data is None:

            if not args:
                raise Exception("No arguments passed to read_csv.")

            # update args with additional path information

            args = list(args)
            file_path = args[0]
            if '://' in file_path:
                pass
            elif self.root_path:
                args[0] = self.root_path + file_path

            # modify kwargs with sensible defaults
            # TODO: modify these depending on data type (timeseries, array, etc.)

            kwargs['parse_dates'] = kwargs.get('parse_dates', True)
            kwargs['index_col'] = kwargs.get('index_col', 0)

            data = pd.read_csv(*args, **kwargs)
            self.store[hashval] = data

        return data
