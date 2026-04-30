import httpx

def test_endpoints():
    # Test registration
    try:
        resp = httpx.post('http://localhost:8001/api/v1/auth/register', 
                          json={'email':'test5@example.com','password':'TestPass123','workspace_name':'Test Workspace'})
        print(f'Registration: {resp.status_code}')
        if resp.status_code == 201:
            print('✅ Registration working!')
            data = resp.json()
            token_received = bool(data.get('access_token'))
            print(f'Token received: {token_received}')
        else:
            print(f'Error: {resp.text[:200]}')
    except Exception as e:
        print(f'Registration error: {e}')

    # Test support bot
    try:
        resp = httpx.post('http://localhost:8001/api/v1/support/chat', 
                          json={'message': 'What plans do you offer?'})
        print(f'Support Bot: {resp.status_code}')
        if resp.status_code == 200:
            print('✅ Support bot working!')
        else:
            print(f'Error: {resp.text[:200]}')
    except Exception as e:
        print(f'Support bot error: {e}')

if __name__ == "__main__":
    test_endpoints()
