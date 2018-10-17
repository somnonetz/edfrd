import numpy as np
from collections import namedtuple


__version__ = '0.1'


def _raw(f, size):
    return f.read(size)


def _str(f, size):
    b = _raw(f, size)
    s = b.decode('ascii', 'ignore').strip()
    while s.endswith('\x00'):
        s = s[:-1]
    return s


def _int(f, size):
    s = _str(f, size)
    return int(s.split('.')[0])


def _dis(f, size):
    _raw(f, size)


EDF_HEADER = [
    ('version', 8, _str),
    ('local_patient_identification', 80, _str),
    ('local_recording_identification', 80, _str),
    ('startdate_of_recording', 8, _str),
    ('starttime_of_recording', 8, _str),
    ('number_of_bytes_in_header_record', 8, _int),
    ('reserved', 44, _dis),
    ('number_of_data_records', 8, _int),
    ('duration_of_a_data_record', 8, _int),
    ('number_of_signals', 4, _int),
]

SIGNAL_HEADER = [
    ('label', 16, _str),
    ('transducer_type', 80, _str),
    ('physical_dimension', 8, _str),
    ('physical_minimum', 8, _int),
    ('physical_maximum', 8, _int),
    ('digital_minimum', 8, _int),
    ('digital_maximum', 8, _int),
    ('prefiltering', 80, _str),
    ('number_of_samples_in_each_data_record', 8, _int),
    ('reserved', 32, _dis)
]


EDF = namedtuple('EDF', [name for name, _, _ in EDF_HEADER] + ['signals'])
Signal = namedtuple('Signal', [name for name, _, _ in SIGNAL_HEADER])


def read_edf(file_path):
    with open(file_path, 'rb') as f:
        edf_header = [func(f, size) for _, size, func in EDF_HEADER]
        number_of_signals = edf_header[-1]
        signal_headers = [[] for _ in range(number_of_signals)]

        for _, size, func in SIGNAL_HEADER:
            for signal_header in signal_headers:
                signal_header.append(func(f, size))

    edf_header.append(tuple((Signal(*signal_header) for signal_header in signal_headers)))

    return EDF(*edf_header)


def read_signal(file_path, edf, index):
    int_size = 2
    edf_header_size = sum([size for _, size, _ in EDF_HEADER])
    signal_header_size = sum([size for _, size, _ in EDF_HEADER])

    pos = edf_header_size + edf.num_signals * signal_header_size

    for i in range(index):
        pos += edf.signals[i].num_samples * int_size

    return np.memmap(file_path, dtype=np.int16, offset=pos, shape=edf.signals[index].num_samples)
