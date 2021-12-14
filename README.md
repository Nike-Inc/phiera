Phiera
---

[![codecov](https://codecov.io/gh/Nike-Inc/phiera/branch/master/graph/badge.svg?token=J9slc2blRx)](https://codecov.io/gh/Nike-Inc/phiera)
[![Test](https://github.com/Nike-Inc/phiera/actions/workflows/python-test.yaml/badge.svg)](https://github.com/Nike-Inc/phiera/actions/workflows/python-test.yaml)
[![PyPi Release](https://github.com/Nike-Inc/phiera/actions/workflows/python-build.yaml/badge.svg)](https://github.com/Nike-Inc/phiera/actions/workflows/python-build.yaml)
![License](https://img.shields.io/pypi/l/phiera)
![Python Versions](https://img.shields.io/pypi/pyversions/phiera)
![Python Wheel](https://img.shields.io/pypi/wheel/phiera)

Phiera is a fork of [Piera](https://github.com/b1naryth1ef/pierahttps://github.com/b1naryth1ef/piera), a lightweight, pure-Python [Hiera](http://docs.puppetlabs.com/hiera/) parser. Piera was originally built to provide Python tooling access to Puppet/Hiera configurations. The original Piera is currently not feature complete; lacking some less-used interpolation and loading features.

Table of content
* [Why](#why)
* [Installation](#installation)
* [Usage](#usage)
* [Unit Tests](#tests)

# <a name="why"></a> Why?:

Piera/Phiera generalizes Puppet Hiera's hierarchical storage system; making a simple, very flexible, abstracted, and DRY mechanism for managing complex configuration data available to a broad set of tooling and applicable to a broad set of problems.

Phiera builds on the original Piera work, adding:
  
  - Python3 compatibility
  - Support for deep merging
  - Support for configuration as a dict

# <a name="installation"></a> Installation:

### From PyPi:
```shell script
pip install phiera
```

### From GitHub:
```shell script
pip install git+https://github.com/Nike-Inc/phiera#egg=phiera
```


### Manually

```bash
git clone git@github.com/Nike-Inc/phiera.git
cd phiera
python setup.py install
```

# <a name="usage"></a> Usage:

```python
import phiera

h = phiera.Hiera("my_hiera.yaml")

# You can use phiera to simply interact with your structured Hiera data

# key: 'value'
assert h.get("key") == "value"

# key_alias: '%{alias('key')}'
assert h.get("key_alias") == "value"

# key_hiera: 'OHAI %{hiera('key_alias')}'
assert h.get("key_hiera") == "OHAI value"

# Give phiera context
assert h.get("my_context_based_key", name='test01', environment='qa') == "context is great!"
```

# <a name="tests"></a> Unit Tests:

```bash
poetry run pytest --cov-report=html --cov=phiera --cov-fail-under=80 tests/
```
