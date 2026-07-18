from fastapi import status
from fastapi.testclient import TestClient


def test_openapi_exposes_internal_api_key_security(
    client: TestClient,
) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == status.HTTP_200_OK

    schema = response.json()
    security_scheme = schema["components"]["securitySchemes"]["InternalApiKey"]

    assert security_scheme["type"] == "apiKey"
    assert security_scheme["in"] == "header"
    assert security_scheme["name"] == "X-API-Key"

    internal_ping = schema["paths"]["/internal/ping"]["get"]

    assert internal_ping["security"] == [
        {
            "InternalApiKey": [],
        }
    ]
