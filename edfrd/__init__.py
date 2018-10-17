import warnings
from collections import namedtuple

import numpy as np


__version__ = '0.2'


def _raw(f, size, _):
    return f.read(size)


def _str(f, size, name):
    b = _raw(f, size, name)
    s = b.decode('ascii', 'ignore').strip()
    while s.endswith('\x00'):
        s = s[:-1]
    return s


def _int(f, size, name):
    s = _str(f, size, name)

    try:
        return int(s)
    except ValueError:
        warnings.warn('{name}: Could not parse integer {s}.'.format(name=name, s=s))

    return None


def _float(f, size, name):
    s = _str(f, size, name)

    try:
        return float(s)
    except ValueError:
        warnings.warn('{name}: Could not parse float {s}.'.format(name=name, s=s))

    return None


def _discard(f, size, name):
    _raw(f, size, name)


EDF_HEADER = [
    ('version', 8, _str),
    ('local_patient_identification', 80, _str),
    ('local_recording_identification', 80, _str),
    ('startdate_of_recording', 8, _str),
    ('starttime_of_recording', 8, _str),
    ('number_of_bytes_in_header_record', 8, _int),
    ('reserved', 44, _discard),
    ('number_of_data_records', 8, _int),
    ('duration_of_a_data_record', 8, _int),
    ('number_of_signals', 4, _int),
]

SIGNAL_HEADER = [
    ('label', 16, _str),
    ('transducer_type', 80, _str),
    ('physical_dimension', 8, _str),
    ('physical_minimum', 8, _float),
    ('physical_maximum', 8, _float),
    ('digital_minimum', 8, _int),
    ('digital_maximum', 8, _int),
    ('prefiltering', 80, _str),
    ('nr_of_samples_in_each_data_record', 8, _int),
    ('reserved', 32, _discard)
]


EDF = namedtuple('EDF', [name for name, _, _ in EDF_HEADER] + ['signals'])
Signal = namedtuple('Signal', [name for name, _, _ in SIGNAL_HEADER])


def read_edf(file_path):
    with open(file_path, 'rb') as f:
        edf_header = [func(f, size, name) for name, size, func in EDF_HEADER]
        number_of_signals = edf_header[-1]
        signal_headers = [[] for _ in range(number_of_signals)]

        for name, size, func in SIGNAL_HEADER:
            for signal_header in signal_headers:
                signal_header.append(func(f, size, name))

    edf_header.append(tuple((Signal(*signal_header) for signal_header in signal_headers)))

    return EDF(*edf_header)


def read_signal(file_path, edf, index):
    int_size = 2
    edf_header_size = sum([size for _, size, _ in EDF_HEADER])
    signal_header_size = sum([size for _, size, _ in EDF_HEADER])

    pos = edf_header_size + edf.number_of_signals * signal_header_size

    for i in range(index):
        pos += edf.signals[i].nr_of_samples_in_each_data_record * int_size

    return np.memmap(file_path, dtype=np.int16, offset=pos, shape=edf.signals[index].nr_of_samples_in_each_data_record)
