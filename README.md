# EMLABPKG

EM Lab: Dr. Evgeny Mikheev's lab in the Physics Department at the University of Cincinnati focuses on fabricating and testing superconducting nanoelectronics with perovskite oxides.\
Emlabpkg is a collection of sub-packages used in conjunction with other scientific libraries for experimental Physics measurement automation, patterns for fabrication etc.

## Installation

```bash
pip install emlabpkg
```

Version history along with other information is available at [PyPi](https://pypi.org/project/emlabpkg/).

## Sub-Package Information

1) Sweep: Sweep is a package from the [measureme](https://github.com/spxtr/measureme) repository by [spxtr](https://github.com/spxtr). This package's code was modified to include some general functionalities like taking notes with measurement sweeps, or getting better metadata with more information and also some functionalities that are specific to EM Lab and our instruments. For more information on sweep's dependencies, installation and usage instructions, visit the [measureme repository](https://github.com/spxtr/measureme).
2) Instrument_drivers: This sub-package contains the Python drivers for NF ZM2376: LCR Meter and R&S ZNLE14: VNA. The drivers were programmed using [QCoDeS](https://qcodes.github.io/Qcodes/) and their custom [VisaInstrument class](https://github.com/QCoDeS/Qcodes/blob/bb781e5dd61027e8e6173f56150a18247a83ee49/qcodes/instrument/visa.py). For more information on qcodes's dependencies, installation and usage instructions, visit the [qcodes repository](https://github.com/QCoDeS/Qcodes).
3) Gdspy_layouts: This module contains programs to create patterns for resonator meanders (as of now) and more (TBD) that are based on [GDSPY](https://gdspy.readthedocs.io/en/stable/#). This library is a way to create complex patterns and then export them in a .gds format that can be used with CAD design software like [KLayout](https://www.klayout.de/). For more information on gdspy's dependencies, installation and usage instructions, visit the [gdspy repository](https://github.com/heitzmann/gdspy).
 
## Usage
There are different usage instructions for the 3 sub-packages. Jupyter notebooks for usage instructions will be added soon. Stay tuned!

## Contributing
Since this is a lab package, contributions are always welcome to keep our experiment methods up-to-date. If there are minor changes, pull requests are good. For major changes, please open an issue first to discuss what you would like to change.
