import httpx

def test_support():
    try:
        resp = httpx.post('http://localhost:8001/api/v1/support/chat', 
                          json={'message': 'What plans do you offer?'})
        print(f'Support Bot Status: {resp.status_code}')
        if resp.status_code == 200:
            print('✅ Support bot working!')
            data = resp.json()
            response = data.get('response', 'No response')
            print(f'Response: {response[:100]}')
        else:
            print(f'Error: {resp.text[:200]}')
    except Exception as e:
        print(f'Support Bot Error: {e}')

if __name__ == "__main__":
    test_support()
