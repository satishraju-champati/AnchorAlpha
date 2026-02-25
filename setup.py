from setuptools import setup, find_packages

setup(
    name="AnchorAlpha",
    version="0.1.0",
    description="Multi-Tier Large-Cap Momentum Screener",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "pandas>=2.0.0",
        "requests>=2.28.0",
        "streamlit>=1.28.0",
        "boto3>=1.26.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ]
    }
)