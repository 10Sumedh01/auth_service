# Auth Service

This project is a Django-based authentication service that provides a flexible and secure way to manage users and applications. It supports various authentication methods, including credentials, magic links, and OAuth with providers like GitHub.

## Features

*   **Application Management:** Create and manage applications that will use the authentication service.
*   **User Management:** Manage users for each application.
*   **Multiple Authentication Methods:**
    *   Email and Password
    *   Magic Links
    *   OAuth 2.0 (GitHub provider included)
*   **API Key Management:** Secure your API with auto-generated API keys.
*   **Developer Dashboard:** A simple interface for developers to manage their applications and users.

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

4.  **Create a `.env` file** in the root directory and add the following environment variables. You can get the email credentials from a service like [Mailtrap](https://mailtrap.io/).

    ```env
    EMAIL_HOST_USER=<your-mailtrap-username>
    EMAIL_HOST_PASSWORD=<your-mailtrap-password>
    ```

5.  **Set up the PostgreSQL database:**

    *   Create a new database named `auth_service_db`.
    *   Update the `DATABASES` setting in `auth_service/settings.py` with your PostgreSQL credentials if they are different from the default.

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

---

## API Documentation

This document provides a detailed explanation of the models, URLs, and views used in the `auth_api` application.

### Data Models (`auth_api/models.py`)

The service uses the following Django models to store data:

#### `App`

Represents an application created by a developer.

-   `app_id` (CharField): A unique identifier for the application (UUID).
-   `name` (CharField): The name of the application.
-   `developer` (ForeignKey to `User`): The developer who owns the application.
-   `created_at` (DateTimeField): The timestamp when the application was created.
-   **Meta:** Ensures that a developer cannot have two apps with the same name.

#### `User`

Represents an end-user of an `App`.

-   `app` (ForeignKey to `App`): The application to which the user belongs.
-   `user_id` (CharField): A unique identifier for the user within the application.
-   `email` (EmailField): The user's email address.
-   `name` (CharField): The user's name (optional).
-   `auth_method` (CharField): The method used for authentication (e.g., `oauth`, `credentials`, `magic_link`).
-   `last_login` (DateTimeField): The timestamp of the user's last login (optional).
-   `created_at` (DateTimeField): The timestamp when the user was created.
-   **Meta:** Ensures that an email address is unique per application.

#### `ApiKey`

Represents an API key for an `App`, used for authenticating API requests.

-   `app` (ForeignKey to `App`): The application the API key belongs to.
-   `key` (CharField): The API key string (UUID).
-   `created_at` (DateTimeField): The timestamp when the key was created.
-   `is_active` (BooleanField): Indicates if the key is currently active.

#### `OAuthConfig`

Stores OAuth configuration for an `App` and a specific provider.

-   `app` (ForeignKey to `App`): The application this configuration belongs to.
-   `provider` (CharField): The OAuth provider (e.g., `github`, `google`).
-   `client_id` (CharField): The OAuth client ID.
-   `client_secret` (CharField): The OAuth client secret.
-   `redirect_uri` (URLField): The callback URL for the OAuth flow.
-   `created_at` (DateTimeField): The timestamp when the configuration was created.
-   **Meta:** Ensures that there is only one configuration per provider for each app.

---

### URL Endpoints (`auth_api/urls.py`)

The following URL patterns are defined to handle API requests:

#### Authentication

-   `auth/credentials/<str:app_id>` -> `CredentialsSignInView`
-   `auth/magic-link/<str:app_id>` -> `MagicLinkView`
-   `auth/verify/<str:app_id>` -> `MagicLinkVerifyView`
-   `auth/<str:provider>/<str:app_id>` -> `OAuthRedirectView`
-   `auth/callback/<str:provider>/<str:app_id>` -> `OAuthCallbackView`

#### User Management

-   `users/<str:app_id>` -> `UserListView`

#### Application Management

-   `apps/` -> `AppListCreateView`

#### API Key Management

-   `apps/<str:app_id>/api-keys` -> `ApiKeyListView`

#### OAuth Configuration Management

-   `apps/<str:app_id>/oauth-configs` -> `OAuthConfigView`

---

### Views (`auth_api/views.py`)

The views handle the logic for each API endpoint.

#### `ApiKeyAuthentication`

A custom authentication class that validates API keys provided in the `Authorization` header.

#### `OAuthRedirectView` (GET)

Initiates the OAuth flow by redirecting the user to the provider's authorization page.

#### `OAuthCallbackView` (POST)

Handles the callback from the OAuth provider, exchanges the authorization code for an access token, retrieves user information, creates or updates the user in the database, and returns a JWT.

#### `CredentialsSignInView` (POST)

Authenticates a user with email and password, creates or updates the user record, and returns a JWT.

#### `MagicLinkView` (POST)

Generates a JWT with the user's information, creates a verification link, and emails it to the user.

#### `MagicLinkVerifyView` (GET)

Verifies the JWT from the magic link, updates the user's `last_login` time, and returns the token.

#### `UserListView` (GET)

Requires API key authentication. Returns a list of all users associated with a given `app_id`.

#### `AppListCreateView` (GET, POST)

Requires developer authentication.
-   **GET**: Lists all applications owned by the authenticated developer.
-   **POST**: Creates a new application for the developer and generates an initial API key.

#### `ApiKeyListView` (GET, POST)

Requires developer authentication.
-   **GET**: Lists all API keys for a given `app_id`.
-   **POST**: Deactivates all existing API keys and creates a new one.

#### `OAuthConfigView` (GET, POST)

Requires developer authentication.
-   **GET**: Lists all OAuth configurations for a given `app_id`.
-   **POST**: Creates a new OAuth configuration for the application.
