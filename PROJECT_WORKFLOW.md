# Project Workflow and Architecture

This document explains the complete workflow of the multi-tenant authentication service.

---

## 1. High-Level Overview

This project is a **multi-tenant authentication service** that also functions as a full **OAuth2 Provider**.

-   **Multi-Tenant:** It allows multiple developers to sign up and create their own applications (`App`). Each application has its own isolated set of users (`User`). This is like a condominium building where each developer owns a condo (an `App`), and each condo has its own residents (the `User`s).
-   **OAuth2 Provider:** It allows third-party applications to securely access data on behalf of an end-user without the user ever sharing their password. This is the "Log in with Google/Facebook" functionality, but with your service acting as the central authority.

### Key Actors

1.  **The Developer (e.g., Alice):** A person who builds an application (like a blog or an e-commerce site). They sign up on your service's dashboard to get API keys and manage their app's users.
2.  **The End-User (e.g., Bob):** A customer of the developer's application. Bob signs up for Alice's blog. His user account is managed by your service but belongs to Alice's app.
3.  **The Third-Party App (e.g., `SuperPhotoPrints.com`):** An external application that wants to connect to Alice's blog on Bob's behalf (e.g., to print his blog photos).

---

## 2. Core Workflows

### Workflow A: The Developer Dashboard

This is the experience for the **Developer (Alice)**.

1.  **Sign Up/Log In:** Alice signs up for an account on your main service (`http://localhost:8000/signup/`). This creates a `DjangoUser` for her.
2.  **Create an App:** Alice logs into the dashboard (`/dashboard/`) and creates a new application, "Alice's Awesome Blog."
3.  **Get Credentials:** Your service generates two sets of credentials for her app:
    -   **API Key:** For her own backend server to talk to your management APIs (e.g., to sign up a user directly).
    -   **OAuth2 Client ID & Secret:** For third-party apps to use when connecting to her app via the OAuth2 flow.
4.  **Manage Users:** Alice can view the list of users who have signed up for her blog.

### Workflow B: End-User Direct Authentication

This is how an **End-User (Bob)** signs up directly for Alice's blog.

1.  **Sign-up on Alice's Blog:** Bob fills out a sign-up form on `alices-awesome-blog.com`.
2.  **Backend API Call:** Alice's server makes a secure, backend API call to your service. This is **not** an OAuth2 flow.
    ```bash
    # Alice's server sends this request to your service
    curl -X POST http://localhost:8000/api/auth/credentials/signup/<alices_app_id> \
    -H "Authorization: Bearer <alices_api_key>" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "bob@example.com",
        "password": "securepassword123"
    }'
    ```
3.  **User Creation:** Your service receives the request, validates Alice's API key, and creates a new `User` record for Bob, linking it to Alice's `App` and a proxy `DjangoUser`.
4.  **Login:** Your service returns a JWT token to Alice's server, which can use it to log Bob in.

### Workflow C: The Full OAuth2 Provider Flow

This is the most complex and powerful workflow. It's how a **Third-Party App** securely connects to a user's account.

1.  **The Request:** Bob is on `SuperPhotoPrints.com` and clicks "Import photos from Alice's Blog."
2.  **Redirect to Authorize:** `SuperPhotoPrints.com` redirects Bob's browser to your service's `/o/authorize/` endpoint with its `client_id` and a `code_challenge`.
3.  **User Consent:** Your service shows Bob a login page. He logs in with his credentials for Alice's blog (`bob@example.com`). He then sees a consent screen: "Do you authorize SuperPhotoPrints.com to access your data?" He clicks **"Allow."**
4.  **Authorization Code:** Your service redirects Bob back to `SuperPhotoPrints.com` with a temporary, one-time-use `code` in the URL.
5.  **Token Exchange:** In the background, the server for `SuperPhotoPrints.com` makes a secure API call to your `/o/token/` endpoint. It sends the `code`, its `client_id`, its `client_secret`, and the `code_verifier`.
6.  **Access Token:** Your service validates everything and returns a powerful `access_token` to `SuperPhotoPrints.com`.
7.  **Access Protected Resources:** `SuperPhotoPrints.com` can now use this `access_token` to make calls to your protected API endpoints (like `/api/me/`) to get Bob's data.
    ```bash
    # SuperPhotoPrints.com server sends this request
    curl -H "Authorization: Bearer <the_access_token>" http://localhost:8000/api/me/
    ```
    Your service returns Bob's profile, because the token proves that Bob granted permission.

### Workflow D: End-User Social Login (GitHub/Google)

This is how an **End-User (Bob)** signs up or logs in to Alice's blog using an existing social account. This flow uses your service as a client to the social provider.

1.  **Click "Login with GitHub"**: On `alices-awesome-blog.com`, Bob clicks a "Login with GitHub" button.
2.  **Backend API Call**: Alice's server makes an API call to your service's `/api/auth/github/<alices_app_id>` endpoint.
3.  **Redirect to Social Provider**: Your service looks up the `OAuthConfig` for Alice's app and redirects Bob's browser to the GitHub authorization page.
4.  **GitHub Consent**: Bob logs into GitHub (if he isn't already) and authorizes the connection.
5.  **Callback to Your Service**: GitHub redirects Bob back to your `/api/auth/callback/github/<alices_app_id>` endpoint with a temporary code.
6.  **User Creation & JWT Generation**: Your service exchanges the code for a GitHub access token, fetches Bob's user info from GitHub's API, creates a corresponding `User` record for Bob within Alice's `App`, and generates a JWT for Bob.
7.  **Final Redirect**: Your service redirects Bob back to the `redirect_uri` specified in Alice's `OAuthConfig`, with the newly generated JWT in the URL parameters. Alice's server can then use this JWT to log Bob in.

### Workflow E: End-User Magic Link Login

This is how an **End-User (Bob)** signs up or logs in without a password.

1.  **Enter Email**: On `alices-awesome-blog.com`, Bob enters his email address into a form and clicks "Send Magic Link".
2.  **Backend API Call**: Alice's server makes a secure API call to your `/api/auth/magic-link/<alices_app_id>` endpoint, sending Bob's email.
3.  **Email Sent**: Your service finds or creates a `User` record for Bob in Alice's `App`, generates a short-lived JWT, and emails a special verification link containing this token to Bob.
4.  **Click Verification Link**: Bob opens his email and clicks the link.
5.  **Verification**: The link points to your `/api/auth/verify/<alices_app_id>` endpoint. Your service receives the request, validates the JWT from the URL, and marks the user as authenticated.
6.  **Login**: The endpoint returns the validated token in a JSON response, which the client application can use to complete the login process.

---
## 3. Architectural Components

-   **`auth_service/settings.py`**: The main project configuration. It registers `oauth2_provider` and sets the `LOGIN_URL`.
-   **`auth_service/urls.py`**: The root URL configuration. It routes dashboard URLs to the dashboard views and includes the URLs for `auth_api` and `oauth2_provider`.
-   **`auth_api/models.py`**: Defines the core data structures:
    -   `App`: Represents a developer's application.
    -   `User`: Represents an end-user belonging to a specific `App`. It's linked to a `DjangoUser` for OAuth2 compatibility.
    -   `ApiKey`: Used for the direct, server-to-server authentication flow.
    -   `OAuthConfig`: Stores the client ID and secret for third-party social login providers (like GitHub, Google) on a per-app basis.
-   **`auth_api/views.py`**: Contains all the API logic:
    -   `CredentialsSignUpView`: Handles direct user sign-ups.
    -   `OAuthRedirectView` & `OAuthCallbackView`: Manages the social login flow.
    -   `MagicLinkView` & `MagicLinkVerifyView`: Manages the passwordless magic link flow.
    -   `UserProfileView`: The OAuth2-protected endpoint that returns user data.
-   `oauth2_provider` (library)**: Automatically provides and manages the critical OAuth2 endpoints:
    -   `/o/authorize/`
    -   `/o/token/`
    -   `/o/introspect/`
    -   And others.

---

## 4. Visualizing the Workflows

Here are simplified diagrams to help visualize the main request flows.

### Direct API Authentication Flow

This flow uses your service's custom API with an `ApiKey`.

```
+------------------------+      (1) Signup Request      +---------------------+
|                        | ---------------------------> |                     |
|   Alice's Awesome      |   (email, password)        |   Your Service      |
|   Blog Server          |                              |   (CredentialsSignUpView) |
|   (Backend)            | <--------------------------- |                     |
|                        |   (2) JWT Token            +---------------------+
+------------------------+   (for Bob)
```

1.  **Signup Request:** The developer's backend server sends the end-user's credentials directly to your `/api/auth/credentials/signup/` endpoint, authenticating itself with its secret `ApiKey`.
2.  **JWT Token:** Your service creates the user and returns a JWT, which the developer's server can use to manage the user's session.

### OAuth2 Provider Flow

This is the standard flow where your service acts as the central identity provider.

```
+-------------------+   (1) Redirect to /authorize   +----------------------+
|                   | -----------------------------> |                      |
|   End-User's      |                                |   Your Service       |
|   Browser (Bob)   |   (4) Redirect with `code`     |   (/o/authorize/)    |
|                   | <----------------------------- |                      |
+--------+----------+                                +-----------+----------+
         |                                                        ^
         | (2) User logs in & consents                            |
         |                                                        |
         v                                                        | (5) Exchange `code` for `token`
+-------------------+                                +------------+---------+
|                   |   (3) Initial Request          |                      |
| Third-Party App   | -----------------------------> |   Your Service       |
| (SuperPhotoPrints)|                                |   (/o/token/)        |
|     Backend       |   (6) Returns `access_token`   |                      |
|                   | <----------------------------- |                      |
+-------------------+                                +----------------------+
```

1.  **Redirect to Authorize:** The third-party app sends the user's browser to your `/o/authorize/` endpoint.
2.  **Login & Consent:** The user logs into your service and grants permission.
3.  **Initial Request:** This is just to show where the flow starts.
4.  **Redirect with `code`:** Your service sends the user's browser back to the third-party app with a temporary `authorization_code`.
5.  **Exchange `code` for `token`:** The third-party app's backend securely sends the `code` and its `client_secret` to your `/o/token/` endpoint.
6.  **Returns `access_token`:** Your service validates everything and returns the powerful `access_token`.

---

## 5. Conclusion

This project successfully combines two powerful concepts: a multi-tenant system for managing app-specific users and a full-featured OAuth2 provider for secure, delegated authentication. By leveraging `django-oauth-toolkit`, the service provides a robust and standards-compliant foundation for developers to build secure and scalable applications.


```