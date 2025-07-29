# Auth Service

This document provides a detailed explanation of the models, URLs, and views used in the `auth_api` and `auth_service` applications.

## Project Overview

This project is a Django-based authentication service designed to provide a centralized and flexible authentication system for multiple applications. It is composed of two main parts:

-   **`auth_api`**: A RESTful API that handles all the core authentication logic, including user management, API key validation, and communication with external OAuth providers.
-   **`auth_service`**: A web-based dashboard that allows developers to register, manage their applications, configure authentication methods, and monitor user activity.

This dual-app architecture separates the core API from the developer-facing interface, allowing for a clean and scalable design.

---

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

### URL Endpoints

#### `auth_api/urls.py`

The following URL patterns are defined to handle API requests:

-   `auth/credentials/signup/<str:app_id>`: Handles user sign-up via email and password.
-   `auth/credentials/signin/<str:app_id>`: Handles user sign-in via email and password.
-   `auth/magic-link/<str:app_id>`: Initiates the magic link authentication process.
-   `auth/verify/<str:app_id>`: Verifies the token from a magic link.
-   `auth/<str:provider>/<str:app_id>`: Redirects the user to the OAuth provider for authorization.
-   `auth/callback/<str:provider>/<str:app_id>`: Handles the callback from the OAuth provider.

#### `auth_service/urls.py`

The following URL patterns are defined for the developer dashboard:

-   `dashboard/`: The main dashboard page, listing all of the developer's applications.
-   `dashboard/app/<str:app_id>/`: The details page for a specific application.
-   `dashboard/app/<str:app_id>/add_oauth_config`: A page for adding a new OAuth configuration.
-   `dashboard/app/<str:app_id>/test_oauth_config/<int:config_id>`: A view for testing an OAuth configuration.
-   `oauth/callback`: The callback URL for the OAuth test flow.
-   `dashboard/<str:app_id>/users`: A page for listing and managing the users of an application.
-   `dashboard/<str:app_id>/users/add`: A page for adding a new user to an application.
-   `dashboard/create_app/`: A page for creating a new application.
-   `apps/<str:app_id>/delete/`: A view for deleting an application.

---

### Views

#### `auth_api/views.py`

-   **`ApiKeyAuthentication`**: A custom authentication class that validates API keys from the `Authorization` header.
-   **`OAuthRedirectView`**: Initiates the OAuth flow by redirecting to the provider's authorization page.
-   **`OAuthCallbackView`**: Handles the callback from the OAuth provider, exchanges the authorization code for an access token, and returns a JWT.
-   **`CredentialsSignUpView`**: Handles user registration with email and password.
-   **`CredentialsSignInView`**: Authenticates a user with email and password and returns a JWT.
-   **`MagicLinkView`**: Sends a magic link to the user's email.
-   **`MagicLinkVerifyView`**: Verifies the magic link token and returns a JWT.

#### `auth_service/views.py`

-   **`dashboard`**: Displays a list of the developer's applications.
-   **`app_details`**: Shows the details of a specific application, including API keys and OAuth configurations.
-   **`add_auth_config`**: Handles the creation of a new OAuth configuration.
-   **`test_oauth_config`**: Initiates a test of an OAuth configuration.
-   **`oauth_callback`**: Handles the callback from the OAuth provider during a test.
-   **`user_list_dashboard`**: Displays a paginated list of users for an application.
-   **`add_user_dashboard`**: Handles the creation of a new user from the dashboard.
-   **`create_app_dashboard`**: Handles the creation of a new application.
-   **`delete_app`**: Handles the deletion of an application.
