# edfrd

edfrd is a Python 3 software library to read EDF files.

## Installation

```bash
pip3 install --user edfrd
```

## Usage

```python
from edfrd import read_header, read_data_records

file_path = 'PATH/TO/FILE.edf'

header = read_header(file_path, calculate_number_of_data_records=True)

data_records = [
    data_record for data_record in
    read_data_records(file_path, header)  # generator
]

for signal_header, signal in zip(header.signals, data_records[0]):
    print(
        signal_header.label,
        signal.size,
        signal.dtype  # numpy int16 array
    )

# optional parameters, default is None
_ = read_data_records(
    file_path,
    header,
    start=0,
    end=header.number_of_data_records
)
```
