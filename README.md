# Auth Service

This project is a Django-based authentication service that provides a flexible and secure way to manage users and applications. It supports various authentication methods, including credentials, magic links, and OAuth with providers like GitHub.

## Key Features

*   **Application Management:** Create and manage applications that will use the authentication service.
*   **User Management:** Manage users for each application.
*   **Multiple Authentication Methods:**
    *   Email and Password
    *   Magic Links
    *   OAuth 2.0 (GitHub provider included)
*   **API Key Management:** Secure your API with auto-generated API keys.
*   **Developer Dashboard:** A simple interface for developers to manage their applications and users.

## Tech Stack

*   **Backend:** Django, Django Rest Framework
*   **Database:** PostgreSQL
*   **Cache:** Redis

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Python 3.8+
*   PostgreSQL
*   Redis
*   Git

### Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd auth_service
    ```

2.  **Create a virtual environment and activate it:**

    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Create a `.env` file** in the root directory and add your email credentials (e.g., from Mailtrap):

    ```env
    EMAIL_HOST_USER=<your-mailtrap-username>
    EMAIL_HOST_PASSWORD=<your-mailtrap-password>
    ```

5.  **Set up the PostgreSQL database:**

    *   Create a new database named `auth_service_db`.
    *   Update the `DATABASES` setting in `auth_service/settings.py` with your PostgreSQL credentials if needed.

6.  **Run the database migrations:**

    ```bash
    python manage.py migrate
    ```

7.  **Create a superuser:**

    ```bash
    python manage.py createsuperuser
    ```

## Running the Application

To run the development server, use the following command:

```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`.

## Running Tests

To run the test suite, use the following command:

```bash
pytest
```

## Contributing

Contributions are welcome! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more details.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Documentation

For more detailed documentation on the API, models, and architecture, please see the [docs](./docs/README.md) directory.