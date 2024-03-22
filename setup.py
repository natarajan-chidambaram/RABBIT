from os import path
from setuptools import setup, find_packages
from codecs import open # To use a consistent encoding


__package__ = 'rabbit'
__version__ = '1.0.0'
__licence__ = 'Apache2.0'
__maintainer__ = 'Natarajan Chidambaram'
__email__ = 'natarajan.chidambaram@umons.ac.be'
__url__ = 'https://github.com/natarajan-chidambaram/RABBIT'
__description__ = 'RABBIT - Rabbit is an Activity Based Bot Identification Tool to detect bot contributors in GitHub repositories based on their recent activity sequences'
__long_description__ = 'This tool accepts the name of a contributor, a GitHub API key and its associated account name and computes its output in four steps.\\\
The first step consists of extracting the public events performed by contributors in GitHub repositories. This step results in a set of events.\\\
The second step identifies activities (belonging to 24 different activity types) performed by the contributor in GitHub repositories. If the number of activties is less than the maximum number of activities, then more events will be collected again. If the total number of activities (from all possible events) are less than specified minimum number of events, then the toll will exit with a message.\\\
The third step constitutes of identifying the contributor behavioural features, namely, mean number of activities per activity type, number of activity types, median time between consecutive activities of different types, number of owners of repositories contributed to, Gini inequality of duration of consecutive activities and mean number of activities per repository.\\\
The forth step simply applies the BIMBAS model that we trained on 140K activities perofrmed by 306 bots and 532 human contributors in GitHub repositories and gives the probability that a contributor is a bot.'
__classifiers__=[
        'Development Status :: 1 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'License :: OSI Approved :: Apache License 2.0',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ]
__requirement__ = [
        'numpy==1.26.4',
        'pandas==2.0.3',
        'tqdm==4.65.1',
        'python-dateutil==2.8.2',
        'scikit-learn == 1.3.0',
        'requests==2.31.0',
        'scipy==1.10.1',
        'urllib3==2.0.6',
        'xgboost==1.7.6'
]

setup(
    name=__package__,

    version=__version__,

    description= __description__,
    long_description=__long_description__,

    url=__url__,

    maintainer=__maintainer__,
    maintainer_email=__email__,

    license=__licence__,

    classifiers=__classifiers__,

    keywords='github contributor activity',

    install_requires = __requirement__,

    include_package_data = True,
    packages = ['.'],

    entry_points={
        'console_scripts': [
            'rabbit=rabbit:cli',
        ]
    },

    py_modules=['rabbit'],
    zip_safe=True,
)
