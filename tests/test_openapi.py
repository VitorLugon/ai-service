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


def test_openapi_documents_ticket_classification(
    client: TestClient,
) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == status.HTTP_200_OK

    schema = response.json()
    operation = schema["paths"]["/internal/tickets/classify"]["post"]

    assert operation["security"] == [
        {
            "InternalApiKey": [],
        }
    ]

    responses = operation["responses"]

    assert "200" in responses
    assert "422" in responses
    assert "503" in responses
