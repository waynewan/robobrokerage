from setuptools import setup
setup(
	author='claude',
	author_email='#',
	description='interacting with popular online brokers',
	license='Apache 2.0',
	name='robobrokerage',
	package_dir={
		'robobrokerage':'robobrokerage',
		'robobrokerage.fidelity':'robobrokerage/fidelity',
	},
	packages=[
		'robobrokerage',
		'robobrokerage.fidelity',
	],
	url='#',
	version='0.1.3.5+clu',
	zip_safe=False
)
