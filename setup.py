from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in e_invoice/__init__.py
from e_invoice import __version__ as version

setup(
	name='e_invoice',
	version=version,
	description='Frappe application to manage einvoicing',
	author='alaabadry1@gmail.com ',
	author_email='alaabadry1@gmail.com ',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
