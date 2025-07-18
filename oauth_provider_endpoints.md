# Core OAuth2 Provider Endpoints Explained

Think of it like this: You are building a secure building (your service) that holds valuable user data. Other applications (we'll call them "clients" or "third-party apps") want to access that data on behalf of your users. OAuth2 is the process of giving those clients a temporary, limited-access keycard instead of the user's master key.

Here are the essential endpoints and their roles in this process.

---

### 1. The `/authorize` Endpoint (The Permission Screen)

This is the **user-facing** part of the flow. Its entire job is to get the user's explicit consent.

*   **What it contains:** A login form (if the user isn't already logged in) followed by a consent screen that asks the user a question like: *"Do you authorize **[Third-Party App Name]** to access your **[list of permissions/scopes, e.g., profile information, photos]**?"*

*   **How it works:**
    1.  A user on a third-party app (e.g., `CoolPhotoEditor.com`) clicks "Log in with YourService".
    2.  `CoolPhotoEditor.com` redirects the user's browser to your `/authorize` endpoint.
    3.  Your service shows the login and consent screen.
    4.  If the user clicks "Allow," your service redirects the user back to `CoolPhotoEditor.com` with a temporary **`authorization_code`** in the URL. This code is *not* the final token; it's just proof of consent.

*   **Use Case:** This is the first step in any "Log in with Google/Facebook/GitHub" flow. It's where the user grants permission.

---

### 2. The `/token` Endpoint (The Secure Key Exchange)

This is a **back-channel** or **server-to-server** endpoint. It's never seen by the user. Its purpose is to securely exchange the temporary `authorization_code` for a real `access_token`.

*   **What it contains:** This endpoint doesn't have a user interface. It's an API that accepts POST requests with specific parameters and returns a JSON object.

*   **How it works:**
    1.  After the user is redirected back to `CoolPhotoEditor.com` with the `authorization_code`, the backend server of `CoolPhotoEditor.com` makes a direct, secure API call to your `/token` endpoint.
    2.  It sends the `authorization_code` along with its own secret credentials (`client_id` and `client_secret`) to prove its identity.
    3.  Your service validates the code and the client's credentials.
    4.  If everything checks out, it returns an **`access_token`** (and often a `refresh_token`) in a JSON response.

*   **Use Case:** This prevents the powerful `access_token` from ever being exposed in the user's browser. By exchanging the code on the back-channel, the process remains secure.

---

### 3. The `/userinfo` Endpoint (Accessing the Data)

This is the endpoint that the third-party app calls to finally get the user's data it was given permission to access.

*   **What it contains:** It's a protected API resource that returns user information (like name, email, user ID, etc.) in a structured format like JSON.

*   **How it works:**
    1.  `CoolPhotoEditor.com`, now holding the `access_token`, makes an API call to your `/userinfo` endpoint.
    2.  It includes the token in the `Authorization` header of the request (e.g., `Authorization: Bearer <the_access_token>`).
    3.  Your service validates the `access_token`. If it's valid and has the correct permissions (scopes), it returns the requested user data.
    4.  If the token is invalid, expired, or doesn't have the right scope, it returns an error.

*   **Use Case:** After logging in, this is how `CoolPhotoEditor.com` would fetch the user's name and profile picture to display on its own site.

### Summary Table

| Endpoint | Who Uses It? | Purpose | Input | Output |
| :--- | :--- | :--- | :--- | :--- |
| `/authorize` | User's Browser | Get user's consent. | `client_id`, `scope`, `redirect_uri` | A redirect with a temporary `authorization_code`. |
| `/token` | Client's Server | Exchange the code for a real token. | `authorization_code`, `client_id`, `client_secret` | A JSON object with the `access_token`. |
| `/userinfo` | Client's Server | Get the user's actual data. | `access_token` in the header. | A JSON object with the user's information. |
