"""Repositorio sobre la tabla DynamoDB del entorno (`client_id`, `sk`)."""

import json

import boto3
from botocore.config import Config

from app.store.base import require_prefix


class DynamoRepository:
    def __init__(self, table_name: str, client=None):
        self._table = table_name
        self._client = client or boto3.client(
            "dynamodb",
            config=Config(connect_timeout=2, read_timeout=5, retries={"max_attempts": 3}),
        )

    @staticmethod
    def _key(client_id: str, sk: str) -> dict:
        return {"client_id": {"S": client_id}, "sk": {"S": sk}}

    def put(
        self, client_id: str, sk: str, document: dict, attributes: dict[str, str] | None = None
    ) -> None:
        item = self._key(client_id, sk)
        item["doc"] = {"S": json.dumps(document)}
        for name, value in (attributes or {}).items():
            item[name] = {"S": value}
        self._client.put_item(TableName=self._table, Item=item)

    def get(self, client_id: str, sk: str) -> dict | None:
        response = self._client.get_item(
            TableName=self._table, Key=self._key(client_id, sk), ConsistentRead=True
        )
        item = response.get("Item")
        return None if item is None else json.loads(item["doc"]["S"])

    def _query(self, client_id: str, prefix: str, **options):
        arguments = {
            "TableName": self._table,
            "KeyConditionExpression": "client_id = :client AND begins_with(sk, :prefix)",
            "ExpressionAttributeValues": {
                ":client": {"S": client_id},
                ":prefix": {"S": require_prefix(prefix)},
            },
            # Lectura consistente: una geocerca recién creada aparece en el listado siguiente.
            "ConsistentRead": True,
            **options,
        }
        while True:
            page = self._client.query(**arguments)
            yield page
            if "LastEvaluatedKey" not in page:
                return
            arguments["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    def list_prefix(self, client_id: str, prefix: str, *, newest_first: bool = False) -> list[dict]:
        pages = self._query(client_id, prefix, ScanIndexForward=not newest_first)
        return [json.loads(item["doc"]["S"]) for page in pages for item in page["Items"]]

    def delete(self, client_id: str, sk: str) -> bool:
        response = self._client.delete_item(
            TableName=self._table, Key=self._key(client_id, sk), ReturnValues="ALL_OLD"
        )
        return "Attributes" in response

    def count_prefix(self, client_id: str, prefix: str) -> int:
        return sum(page["Count"] for page in self._query(client_id, prefix, Select="COUNT"))

    def increment(self, client_id: str, sk: str, *, expires_at: int | None = None) -> int:
        """Contador atómico (`ADD`), compartido por todas las instancias del servicio."""
        expression = "ADD #count :one"
        names = {"#count": "count"}
        values = {":one": {"N": "1"}}
        if expires_at is not None:
            # La tabla borra el elemento después de `expires_at` (TTL de DynamoDB).
            expression += " SET #expires = :expires"
            names["#expires"] = "expires_at"
            values[":expires"] = {"N": str(expires_at)}
        response = self._client.update_item(
            TableName=self._table,
            Key=self._key(client_id, sk),
            UpdateExpression=expression,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="UPDATED_NEW",
        )
        return int(response["Attributes"]["count"]["N"])
