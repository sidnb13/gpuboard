from setuptools import setup, find_namespace_packages

def read_requirements(filename):
    with open(filename) as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

setup(
    name="gpu-monitor",
    version="0.1.0",
    packages=find_namespace_packages(include=["gpu_monitor*", "agent*"]),
    install_requires=read_requirements("requirements-dev.txt"),
    extras_require={
        "agent": read_requirements("requirements-agent.txt"),
        "monitor": read_requirements("requirements-monitor.txt"),
    }
)