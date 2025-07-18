# Manual OAuth2 Provider Testing Guide

This document outlines the steps to manually test that the service is working as a compliant OAuth2 Provider using the Authorization Code Grant with PKCE.

---

### 1. Prerequisites: Create a Test User

First, you need a non-developer user account to act as the resource owner who grants permission.

```bash
# Connect to the Django shell
/home/sumedh/auth_prj/venv/bin/python3 manage.py shell

# Inside the shell, run this Python code
from django.contrib.auth.models import User
if not User.objects.filter(username='testuser').exists():
    user = User.objects.create_user('testuser', password='testpassword123')
    print("Test user created.")
else:
    user = User.objects.get(username='testuser')
    user.set_password('testpassword123')
    user.save()
    print("Test user password has been set.")
```

---

### 2. Create a Test OAuth2 Client Application

Next, create a client application that will request access to the user's data. This represents a third-party application like "SuperPhotoPrints.com".

```bash
# Connect to the Django shell
/home/sumedh/auth_prj/venv/bin/python3 manage.py shell

# Inside the shell, run this Python code
from django.contrib.auth.models import User
from oauth2_provider.models import get_application_model
Application = get_application_model()
developer = User.objects.get(username='your_developer_username') # Change to your superuser/developer username

app, _ = Application.objects.get_or_create(
    name='Test OAuth App',
    user=developer,
    defaults={
        'client_type': 'confidential',
        'authorization_grant_type': 'authorization-code',
        'redirect_uris': 'https://www.google.com/' # A dummy callback for testing
    }
)
print(f"CLIENT_ID={app.client_id}")
print(f"CLIENT_SECRET={app.client_secret}") # Note: This is the HASHED secret.
```
**Important**: The `client_secret` printed here is hashed. To get a raw secret for testing, you must reset it.

```bash
# Inside the shell, run this Python code to get a usable secret
from oauth2_provider.generators import generate_client_secret
new_secret = generate_client_secret()
app.client_secret = new_secret
app.save()
print(f"RAW_CLIENT_SECRET={new_secret}") # Use THIS secret for testing
```

---

### 3. Perform the Authorization Flow

This is the core of the test.

#### Step 3.1: Generate PKCE Codes

The service requires PKCE for security. Generate the necessary codes.

```bash
# Run this command in your terminal
/home/sumedh/auth_prj/venv/bin/python3 -c "
import hashlib, base64, os
code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode('utf-8').rstrip('=')
code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode('utf-8')).digest()).decode('utf-8').rstrip('=')
print(f'CODE_VERIFIER={code_verifier}')
print(f'CODE_CHALLENGE={code_challenge}')
"
```
**Save the `CODE_VERIFIER` and `CODE_CHALLENGE` values.**

#### Step 3.2: Get the Authorization Code

1.  In a browser, log in to the service as `testuser` at `http://localhost:8000/login/`.
2.  In the same browser, construct and visit the following URL. Replace the placeholders with your `CLIENT_ID` and the `CODE_CHALLENGE` you just generated.

    ```
    http://localhost:8000/o/authorize/?response_type=code&client_id=<YOUR_CLIENT_ID>&redirect_uri=https://www.google.com/&code_challenge=<YOUR_CODE_CHALLENGE>&code_challenge_method=S256
    ```
3.  Click "Authorize" on the consent screen.
4.  You will be redirected to Google. Copy the `code` value from the URL in the address bar.

#### Step 3.3: Exchange the Code for an Access Token

Use `curl` to simulate the client's backend exchanging the code for a token. Replace all placeholders with your saved values.

```bash
curl -X POST -H "Content-Type: application/x-www-form-urlencoded" \
-d "grant_type=authorization_code&code=<CODE_FROM_BROWSER>&redirect_uri=https://www.google.com/&client_id=<YOUR_CLIENT_ID>&client_secret=<YOUR_RAW_CLIENT_SECRET>&code_verifier=<YOUR_CODE_VERIFIER>" \
http://localhost:8000/o/token/
```

This will return a JSON object containing the `access_token`.

---

### 4. Test the Protected Endpoint

Use the `access_token` to call the protected `/api/me/` endpoint.

```bash
# Replace <YOUR_ACCESS_TOKEN> with the token from the previous step
curl -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" http://localhost:8000/api/me/
```

If successful, this will return the JSON profile of the `testuser`, confirming the entire flow works.
