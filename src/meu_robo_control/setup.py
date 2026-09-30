import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'meu_robo_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Instala os arquivos YAML de configuração da pasta config/
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Maria Thereza',
    maintainer_email='maitheyu@gmail.com',
    description='Pacote de controle de pose, missao e trajetoria para a Pratica 3',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'pose_control_node = meu_robo_control.pose_control_node:main',
            'mission_node = meu_robo_control.mission_node:main',
            'trajectory_node = meu_robo_control.trajectory_node:main',
        ],
    },
)