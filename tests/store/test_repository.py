"""La misma batería se ejecuta contra el repositorio en memoria y contra DynamoDB simulado."""

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from app.config import Settings
from app.main import create_app
from app.store.base import MemoryRepository
from app.store.dynamodb import DynamoRepository
from tests.helpers import field_payload

TABLE = "nasa-farm-test-app"
A, B = "client-a", "client-b"


class SmallPages:
    """Cliente DynamoDB que fuerza páginas de 2 elementos para ejercitar la paginación."""

    def __init__(self, client):
        self._client = client
        self.queries = 0

    def query(self, **arguments):
        self.queries += 1
        return self._client.query(**arguments, Limit=2)

    def __getattr__(self, name):
        return getattr(self._client, name)


@pytest.fixture
def dynamodb(monkeypatch):
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.setenv(name, "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        client = boto3.client("dynamodb", region_name="us-east-1")
        client.create_table(
            TableName=TABLE,
            KeySchema=[
                {"AttributeName": "client_id", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "client_id", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield client


@pytest.fixture(params=["memory", "dynamodb"])
def repo(request):
    if request.param == "memory":
        return MemoryRepository()
    return DynamoRepository(TABLE, SmallPages(request.getfixturevalue("dynamodb")))


def test_get_returns_what_was_put(repo):
    document = {"id": "1", "name": "Ñandú", "nested": {"values": [1, 2.5, None, True]}}
    repo.put(A, "field#1", document)
    assert repo.get(A, "field#1") == document
    assert repo.get(A, "field#2") is None


def test_put_replaces_and_stored_documents_are_isolated_from_callers(repo):
    document = {"id": "1", "tags": ["a"]}
    repo.put(A, "field#1", document)
    document["tags"].append("mutated-after-put")
    repo.get(A, "field#1")["tags"].append("mutated-after-get")
    assert repo.get(A, "field#1") == {"id": "1", "tags": ["a"]}
    repo.put(A, "field#1", {"id": "1", "tags": []})
    assert repo.get(A, "field#1") == {"id": "1", "tags": []}
    assert repo.count_prefix(A, "field#") == 1


def test_clients_do_not_see_each_other(repo):
    repo.put(A, "field#1", {"owner": "a"})
    repo.put(B, "field#1", {"owner": "b"})
    assert repo.get(A, "field#1") == {"owner": "a"}
    assert repo.list_prefix(B, "field#") == [{"owner": "b"}]
    assert repo.delete(B, "field#1") is True
    assert repo.get(A, "field#1") == {"owner": "a"}
    assert repo.count_prefix(B, "field#") == 0


def test_list_and_count_by_prefix_in_key_order(repo):
    for key in ("field#3", "field#1", "conv#9", "field#2", "field#5", "field#4"):
        repo.put(A, key, {"sk": key})
    ascending = [f"field#{n}" for n in range(1, 6)]
    assert [doc["sk"] for doc in repo.list_prefix(A, "field#")] == ascending
    assert [doc["sk"] for doc in repo.list_prefix(A, "field#", newest_first=True)] == ascending[
        ::-1
    ]
    assert repo.count_prefix(A, "field#") == 5
    assert repo.count_prefix(A, "conv#") == 1
    assert repo.list_prefix(A, "msg#") == []
    assert repo.count_prefix("nobody", "field#") == 0


def test_an_empty_prefix_is_rejected(repo):
    with pytest.raises(ValueError):
        repo.count_prefix(A, "")
    with pytest.raises(ValueError):
        repo.list_prefix(A, "")


def test_delete_reports_whether_the_item_existed(repo):
    repo.put(A, "field#1", {"id": "1"})
    assert repo.delete(A, "field#1") is True
    assert repo.delete(A, "field#1") is False
    assert repo.get(A, "field#1") is None


def test_dynamodb_item_carries_first_level_attributes(dynamodb):
    repo = DynamoRepository(TABLE, dynamodb)
    attributes = {
        "cell_id": "E9_r0463_c0846",
        "kind": "field",
        "created_at": "2026-11-14T20:00:00Z",
    }
    repo.put(A, "field#1", {"id": "1"}, attributes)
    item = dynamodb.get_item(TableName=TABLE, Key={"client_id": {"S": A}, "sk": {"S": "field#1"}})[
        "Item"
    ]
    assert {name: value["S"] for name, value in item.items()} == {
        "client_id": A,
        "sk": "field#1",
        "doc": '{"id": "1"}',
        **attributes,
    }


def test_dynamodb_follows_pagination(dynamodb):
    pages = SmallPages(dynamodb)
    repo = DynamoRepository(TABLE, pages)
    for index in range(5):
        repo.put(A, f"field#{index}", {"n": index})
    assert [doc["n"] for doc in repo.list_prefix(A, "field#")] == [0, 1, 2, 3, 4]
    assert pages.queries >= 3
    assert repo.count_prefix(A, "field#") == 5


def test_app_table_selects_dynamodb_and_fields_survive_a_restart(dynamodb, monkeypatch):
    monkeypatch.setenv("APP_TABLE", TABLE)
    headers = {"X-Client-Id": "3f2b8c1e-7a4d-4e9b-9c55-0d1e2f3a4b5c"}
    first = create_app(Settings(environment="pr-42"))
    assert isinstance(first.state.repository, DynamoRepository)
    created = TestClient(first).post("/api/v1/fields", json=field_payload(), headers=headers)
    assert created.status_code == 201
    # Un proceso nuevo, como tras reiniciar o redesplegar el contenedor.
    restarted = TestClient(create_app(Settings(environment="pr-42")))
    assert restarted.get("/api/v1/fields", headers=headers).json() == [created.json()]
    item = dynamodb.scan(TableName=TABLE)["Items"][0]
    assert item["sk"]["S"] == f"field#{created.json()['id']}"
    assert (item["cell_id"]["S"], item["kind"]["S"]) == ("E9_r0463_c0846", "field")
    assert item["created_at"]["S"] == created.json()["created_at"]


def test_without_app_table_the_repository_is_in_memory(monkeypatch):
    monkeypatch.delenv("APP_TABLE", raising=False)
    assert isinstance(create_app(Settings()).state.repository, MemoryRepository)
