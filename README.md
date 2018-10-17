# edfrd

edfrd is a Python 3 software library to read EDF files.

## Installation

```bash
pip3 install --user edfrd
```

## Usage

```python
from edfrd import read_edf, read_data_records

file_path = 'PATH/TO/FILE.edf'

edf = read_edf(file_path)  # namedtuple

data_records = [
    data_record for data_record in
    read_data_records(file_path, edf)  # generator
]

assert len(data_records[0]) == edf.number_of_signals
```
