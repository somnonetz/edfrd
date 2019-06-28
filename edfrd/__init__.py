import os
from collections import namedtuple
import warnings
import numpy as np


__version__ = '0.6'


def _str(f, size, _):
    s = f.read(size).decode('ascii', 'ignore').strip()
    while s.endswith('\x00'):
        s = s[:-1]
    return s


def _int(f, size, name):
    s = _str(f, size, name)
    try:
        return int(s)
    except ValueError:
        warnings.warn('{name}: Could not parse integer {s}.'.format(name=name, s=s))


def _float(f, size, name):
    s = _str(f, size, name)
    try:
        return float(s)
    except ValueError:
        warnings.warn('{name}: Could not parse float {s}.'.format(name=name, s=s))


def _discard(f, size, _):
    f.read(size)


HEADER = (
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
)


SIGNAL_HEADER = (
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
)


INT_SIZE = 2
HEADER_SIZE = sum([size for _, size, _ in HEADER])
SIGNAL_HEADER_SIZE = sum([size for _, size, _ in SIGNAL_HEADER])


Header = namedtuple('Header', [name for name, _, _ in HEADER] + ['signals'])
SignalHeader = namedtuple('SignalHeader', [name for name, _, _ in SIGNAL_HEADER])


def read_header(file_path, calculate_number_of_data_records=None):
    with open(file_path, 'rb') as f:
        header = [func(f, size, name) for name, size, func in HEADER]
        number_of_signals = header[-1]
        signal_headers = [[] for _ in range(number_of_signals)]

        for name, size, func in SIGNAL_HEADER:
            for signal_header in signal_headers:
                signal_header.append(func(f, size, name))

    header.append(tuple((SignalHeader(*signal_header) for signal_header in signal_headers)))

    if calculate_number_of_data_records:
        data_record_size = sum([signal.nr_of_samples_in_each_data_record for signal in header[-1]]) * INT_SIZE
        file_size_without_headers = os.path.getsize(file_path) - (HEADER_SIZE + SIGNAL_HEADER_SIZE * number_of_signals)

        if file_size_without_headers % data_record_size != 0:
            warnings.warn('file_size_without_headers {fswh} is not a multiple of data_record_size {drs}'.format(
                fswh=file_size_without_headers,
                drs=data_record_size
            ))

        calculated_number_of_data_records = file_size_without_headers // data_record_size
        number_of_data_records = header[7]

        if calculated_number_of_data_records != number_of_data_records:
            warnings.warn('number_of_data_records {n} in header does not match calculated number {cn}'.format(
                n=number_of_data_records,
                cn=calculated_number_of_data_records
            ))

        header[7] = calculated_number_of_data_records

    return Header(*header)


def read_data_records(file_path, header, start=None, end=None):
    start = start if start is not None else 0
    end = end if end is not None else header.number_of_data_records
    data_record_length = sum([signal.nr_of_samples_in_each_data_record for signal in header.signals])

    with open(file_path, 'rb') as f:
        f.seek(HEADER_SIZE + header.number_of_signals * SIGNAL_HEADER_SIZE + start * data_record_length * INT_SIZE)

        for _ in range(start, end):
            a = np.fromfile(f, count=data_record_length, dtype=np.int16)

            data_record = []
            offset = 0

            for signal in header.signals:
                data_record.append(a[offset:offset + signal.nr_of_samples_in_each_data_record])
                offset += signal.nr_of_samples_in_each_data_record

            yield data_record
