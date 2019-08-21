# edfrd

edfrd is a Python 3 software library to **read** and **write** EDF files.

It is designed as a low-level library, that does not interpret the EDF data whenever possible. Therefore, edfrd can
read files even if non-standard values are contained in the header.

Data records are loaded as `int16` arrays using numpy.


## Installation

```bash
pip3 install --user edfrd
```


## Reading EDF Header and Data Records

```python
from edfrd import read_header, read_data_records

file_path = 'PATH/TO/FILE.edf'

header = read_header(file_path)
print(header)

for data_record in read_data_records(file_path, header):  # generator
    # iterate through data_records
    break

for signal in data_record:
    # iterate through signal arrays of a single data_record
    print(signal.size)

for signal_header, signal in zip(header.signals, data_record):
    # iterate through signal headers and signal arrays
    print(signal_header.label, signal.size)
```

If the header of your EDF file does not correctly specifiy the number of data records, you can use the following option
to calculate it from the file size.

```python
header = read_header(file_path, calculate_number_of_data_records=True)
```

You can try parsing the `startdate_of_recording` and `starttime_of_recording` as integer tuples. If parsing fails the
original string will be returned.

```python
header = read_header(file_path, parse_date_time=True)

day, month, year = header.startdate_of_recording
hours, minutes, seconds = header.starttime_of_recording
```

The number of data records being read can be limited by specifying an optional `start` or `end` index.

```python
for data_record in read_data_records(file_path, header, start=0, end=header.number_of_data_records):
    break
```

To work with larger chunks of a signal than provided by a data record, consider creating a new numpy array as a
`buffer`.

```python
import numpy as np
from edfrd import read_header, read_data_records

file_path = 'PATH/TO/FILE.edf'

header = read_header(file_path)
start, end = 2, 4
signal_index = 0
signal_header = header.signals[signal_index]
buffer_length = (end - start) * signal_header.nr_of_samples_in_each_data_record
buffer = np.empty(buffer_length, dtype=np.int16)
pointer = 0

for data_record in read_data_records(start, end):
    buffer[pointer:pointer+signal_header.nr_of_samples_in_each_data_record] = data_record[signal_index]
    pointer += signal_header.nr_of_samples_in_each_data_record

print(buffer)
```

You can also pass a file descriptor (`fr`) instead of a string (`file_path`). Note that `read_data_records` will
continue from the current byte position, where `read_header` stopped, without performing an additional seek operation.

```python
with open(file_path, 'rb') as fr:
    header = read_header(fr)

    for data_record in read_data_records(fr, header):
        break
```


## Writing EDF Header and Data Records

```python
from edfrd import read_header, read_data_records, write_header, write_data_records

file_path = 'PATH/TO/FILE.edf'
new_file_path = 'PATH/TO/NEW_FILE.edf'

header = read_header(file_path)
data_records = read_data_records(file_path, header)
write_header(file_path, header)
write_data_records(file_path, data_records)
```

Again, using file descriptors (`fr` and `fw`) is possible.

```python
with open(file_path, 'rb') as fr:
    header = read_header(fr)
    data_records = read_data_records(fr, header)
    
    with open(new_file_path, 'wb') as fw:
        write_header(fw, header)
        write_data_records(fw, data_records)
```
