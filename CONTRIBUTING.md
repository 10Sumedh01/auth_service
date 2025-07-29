# Contributing to the Project

We love seeing contributions from the community and welcome your help! Please read the following guidelines to ensure a smooth and effective contribution process.

## How to Report Bugs

If you find a bug, please create an issue in the GitHub repository. A great bug report includes:

- A clear and descriptive title.
- A detailed description of the problem, including the exact steps to reproduce it.
- What you expected to happen and what actually happened.
- Information about your environment (e.g., OS, Python version, browser).

## How to Suggest Features

If you have an idea for a new feature, please open an issue to start a discussion. This allows us to align on the feature's scope and design before you invest time in writing code.

## Development Workflow

1.  **Fork the repository** and clone it to your local machine.
2.  **Create a feature branch** from the `main` branch: `git checkout -b your-feature-name`.
3.  **Set up your environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
4.  **Make your changes**. Ensure you follow the project's coding standards.
5.  **Write tests** for your new feature or bug fix.
6.  **Run the tests** to ensure everything is working correctly: `pytest`.
7.  **Commit your changes** with a clear and descriptive commit message.
8.  **Push your branch** to your fork: `git push origin your-feature-name`.
9.  **Open a pull request** to the `main` branch of the original repository.

## Coding Standards

- We follow the **PEP 8** style guide for Python code.
- We use the **Black** code formatter to maintain a consistent style. Before committing, please format your code:
  ```bash
  pip install black
  black .
  ```
- Write clear, readable, and well-commented code, especially for complex logic.

Thank you for contributing!
