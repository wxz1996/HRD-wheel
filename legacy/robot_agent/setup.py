from setuptools import find_packages, setup


package_name = "robot_agent"


setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/robot_agent.launch.py"]),
    ],
    install_requires=["setuptools", "paho-mqtt"],
    zip_safe=True,
    maintainer="robot-agent",
    maintainer_email="dev@example.com",
    description="ROS2 robot agent with MQTT bridge for capture_image.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "capture_agent = robot_agent.capture_agent_node:main",
        ],
    },
)
