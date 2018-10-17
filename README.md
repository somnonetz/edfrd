# edfrd

edfrd is a Python 3 software library to read EDF files.

## Installation

```bash
pip3 install --user edfrd
```

## Usage

```python
from edfrd import read_edf, read_signal

file_path = 'PATH/TO/FILE.edf'

edf = read_edf(file_path)

signals = [
    read_signal(file_path, edf, i)
    for i in range(edf.number_of_signals)
]
```
