def test_root_endpoint(client):
    """Test the root endpoint returns a successful status and JSON content."""
    response = client.get('/')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/json'
    json_data = response.get_json()
    assert json_data['status'] == 'online'
    assert 'CROT Backend is running' in json_data['message']

def test_providers_endpoint(client):
    """Test the /providers endpoint returns a successful status and a JSON list."""
    response = client.get('/providers')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/json'
    json_data = response.get_json()
    assert isinstance(json_data, list)
    # Check if the default ollama provider is present
    assert any(p['name'] == 'ollama' for p in json_data)

def test_sessions_endpoint(client):
    """Test the /sessions endpoint returns a successful status and a JSON list."""
    response = client.get('/sessions')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/json'
    json_data = response.get_json()
    assert isinstance(json_data, list)
