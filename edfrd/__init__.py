import os
from collections import namedtuple
import warnings
import numpy as np


__version__ = '0.7'


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


def _split_date_or_time(s):
    a, b, c = None, None, None
    try:
        a, b, c = s.split('.')
    except:
        try:
            a, b, c = s.split(':')
        except:
            pass
    return int(a), int(b), int(c)


def _parse_date(s):
    try:
        day, month, year = _split_date_or_time(s)
        assert 1 <= day <= 31
        assert 1 <= month <= 12
        assert 0 <= year <= 99
        if year < 85:
            year += 2000
        else:
            year += 1900
    except Exception:
        warnings.warn(f'could not parse date {s}')
        return s
    return day, month, year


def _parse_time(s):
    try:
        hours, minutes, seconds = _split_date_or_time(s)
        assert 0 <= hours <= 23
        assert 0 <= minutes <= 59
        assert 0 <= seconds <= 59
    except Exception:
        warnings.warn(f'could not parse time {s}')
        return s
    return hours, minutes, seconds


def read_header(fd, calculate_number_of_data_records=None, parse_date_time=None):
    opened = False
    if isinstance(fd, str):
        opened = True
        fd = open(fd, 'rb')

    try:
        header = [func(fd, size, name) for name, size, func in HEADER]
        number_of_signals = header[-1]
        signal_headers = [[] for _ in range(number_of_signals)]

        for name, size, func in SIGNAL_HEADER:
            for signal_header in signal_headers:
                signal_header.append(func(fd, size, name))

        file_size = os.fstat(fd.fileno()).st_size
    finally:
        if opened:
            fd.close()

    header.append(tuple((SignalHeader(*signal_header) for signal_header in signal_headers)))

    if calculate_number_of_data_records:
        data_record_size = sum([signal.nr_of_samples_in_each_data_record for signal in header[-1]]) * INT_SIZE
        file_size_without_headers = file_size - (HEADER_SIZE + SIGNAL_HEADER_SIZE * number_of_signals)

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

    if parse_date_time:
        header[3] = _parse_date(header[3])
        header[4] = _parse_time(header[4])

    return Header(*header)


def read_data_records(fd, header, start=None, end=None):
    opened = False
    if isinstance(fd, str):
        opened = True
        fd = open(fd, 'rb')

    try:
        start = start if start is not None else 0
        end = end if end is not None else header.number_of_data_records
        data_record_length = sum([signal.nr_of_samples_in_each_data_record for signal in header.signals])

        if opened:
            fd.seek(HEADER_SIZE + header.number_of_signals * SIGNAL_HEADER_SIZE + start * data_record_length * INT_SIZE)

        for _ in range(start, end):
            a = np.fromfile(fd, count=data_record_length, dtype=np.int16)

            data_record = []
            offset = 0

            for signal in header.signals:
                data_record.append(a[offset:offset + signal.nr_of_samples_in_each_data_record])
                offset += signal.nr_of_samples_in_each_data_record

            yield data_record
    finally:
        if opened:
            fd.close()


def write_header(fd, header):
    opened = False
    if isinstance(fd, str):
        opened = True
        fd = open(fd, 'wb')

    try:
        for val, (name, size, _) in zip(header, HEADER):
            if val is None:
                val = b'\x20' * size

            if not isinstance(val, bytes):
                if (name == 'startdate_of_recording' or name == 'starttime_of_recording') and not isinstance(val, str):
                    val = '{:02d}.{:02d}.{:02d}'.format(val[0], val[1], val[2] % 100)
                val = str(val).encode(encoding='ascii').ljust(size, b'\x20')

            assert len(val) == size
            fd.write(val)

        for vals, (name, size, _) in zip(zip(*header.signals), SIGNAL_HEADER):
            for val in vals:
                if val is None:
                    val = b'\x20' * size

                if not isinstance(val, bytes):
                    val = str(val).encode(encoding='ascii').ljust(size, b'\x20')

                assert len(val) == size
                fd.write(val)
    finally:
        if opened:
            fd.close()


def write_data_records(fd, data_records):
    opened = False
    if isinstance(fd, str):
        opened = True
        fd = open(fd, 'ab')

    try:
        for data_record in data_records:
            for signal in data_record:
                signal.tofile(fd)
    finally:
        if opened:
            fd.close()
