"""Stream type classes for tap-shopify."""

import logging

from decimal import Decimal
from pathlib import Path
from typing import Optional

from tap_shopify.client import tap_shopifyStream

SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


log = logging.getLogger(__name__)


class AbandonedCheckouts(tap_shopifyStream):
    """Abandoned checkouts stream."""

    name = "abandoned_checkouts"
    path = "/checkouts.json"
    records_jsonpath = "$.checkouts[*]"
    primary_keys = ["id"]
    replication_key = "updated_at"
    schema_filepath = SCHEMAS_DIR / "abandoned_checkout.json"


class CollectStream(tap_shopifyStream):
    """Collect stream."""

    name = "collects"
    path = "/collects.json"
    records_jsonpath = "$.collects[*]"
    primary_keys = ["id"]
    replication_key = "id"
    schema_filepath = SCHEMAS_DIR / "collect.json"

    def get_url_params(self, context, next_page_token):
        """Return a dictionary of values to be used in URL parameterization."""
        params = super().get_url_params(context, next_page_token)

        if not next_page_token:
            context_state = self.get_context_state(context)
            last_id = context_state.get("replication_key_value")

            params["since_id"] = last_id

        return params


class CustomCollections(tap_shopifyStream):
    """Custom collections stream."""

    name = "custom_collections"
    path = "/custom_collections.json"
    records_jsonpath = "$.custom_collections[*]"
    primary_keys = ["id"]
    replication_key = "updated_at"
    schema_filepath = SCHEMAS_DIR / "custom_collection.json"


class CustomersStream(tap_shopifyStream):
    """Customers stream."""

    name = "customers"
    path = "/customers.json"
    records_jsonpath = "$.customers[*]"
    primary_keys = ["id"]
    replication_key = "updated_at"
    schema_filepath = SCHEMAS_DIR / "customer.json"


class LocationsStream(tap_shopifyStream):
    """Locations stream."""

    name = "locations"
    path = "/locations.json"
    records_jsonpath = "$.locations[*]"
    primary_keys = ["id"]
    schema_filepath = SCHEMAS_DIR / "location.json"

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return a context dictionary for child streams."""
        return {"location_id": record["id"]}


class InventoryLevelsStream(tap_shopifyStream):
    """Inventory levels stream."""

    parent_stream_type = LocationsStream

    name = "inventory_levels"
    path = "/inventory_levels.json"
    records_jsonpath = "$.inventory_levels[*]"
    primary_keys = ["inventory_item_id"]
    schema_filepath = SCHEMAS_DIR / "inventory_level.json"

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return a context dictionary for child streams."""
        return {"inventory_item_id": record["inventory_item_id"]}

    def get_url_params(self, context, next_page_token):
        """Return a dictionary of values to be used in URL parameterization."""
        params = super().get_url_params(context, next_page_token)

        if not next_page_token:
            params["location_ids"] = context["location_id"]

        return params


class InventoryItemsStream(tap_shopifyStream):
    """Inventory items stream."""

    parent_stream_type = InventoryLevelsStream

    name = "inventory_items"
    path = "/inventory_items/{inventory_item_id}.json"
    records_jsonpath = "$.inventory_item"
    primary_keys = ["id"]
    schema_filepath = SCHEMAS_DIR / "inventory_item.json"


class MetafieldsStream(tap_shopifyStream):
    """Metafields stream."""

    name = "metafields"
    path = "/metafields.json"
    records_jsonpath = "$.metafields[*]"
    primary_keys = ["id"]
    replication_key = "updated_at"
    schema_filepath = SCHEMAS_DIR / "metafield.json"


class OrdersStream(tap_shopifyStream):
    """Orders stream."""

    name = "orders"
    path = "/orders.json"
    records_jsonpath = "$.orders[*]"
    primary_keys = ["id"]
    replication_key = "updated_at"
    schema_filepath = SCHEMAS_DIR / "order.json"

    def post_process(self, row: dict, context: Optional[dict] = None):
        """Perform syntactic transformations only."""
        row = super().post_process(row, context)

        if row:
            row["subtotal_price"] = Decimal(row["subtotal_price"])
            row["total_price"] = Decimal(row["total_price"])
            row["total_discounts"] = Decimal(row["total_discounts"])
            row["total_line_items_price"] = Decimal(row["total_line_items_price"])
            row["total_tax"] = Decimal(row["total_tax"])
            row["total_outstanding"] = Decimal(row["total_outstanding"])

            row["current_subtotal_price"] = Decimal(row["current_subtotal_price"])
            row["current_total_discounts"] = Decimal(row["current_total_discounts"])
            row["current_total_price"] = Decimal(row["current_total_price"])
            row["current_total_tax"] = Decimal(row["current_total_tax"])

        return row

    def get_child_context(self, record: dict, context: Optional[dict]) -> dict:
        """Return a context dictionary for child streams."""
        if record["current_total_price"] < record["total_price"]:
            return {"order_id": record["id"]}

        return None

    def get_url_params(self, context, next_page_token):
        """Return a dictionary of values to be used in URL parameterization."""
        params = super().get_url_params(context, next_page_token)

        if not next_page_token:
            params["status"] = "any"

        return params


class RefundsStream(tap_shopifyStream):
    """Refunds stream."""

    name = "refunds"
    path = "/orders/{order_id}/refunds.json"
    parent_stream_type = OrdersStream
    ignore_parent_replication_key = False
    records_jsonpath = "$.refunds[*]"
    primary_keys = ["id"]
    replication_key = "created_at"
    schema_filepath = SCHEMAS_DIR / "refund.json"

    def read_records(
        self, sync_mode, stream_slice=None, stream_state=None, context=None
    ):
        if context is not None:
            return super().read_records(sync_mode, stream_slice, stream_state, context)


class OrderMetafieldsStream(MetafieldsStream):
    """Metafields stream."""

    name = "order_metafields"
    path = "/orders/{order_id}/metafields.json"
    parent_stream_type = OrdersStream
    ignore_parent_replication_key = True


class ProductsStream(tap_shopifyStream):
    """Products stream."""

    name = "products"
    path = "/products.json"
    records_jsonpath = "$.products[*]"
    primary_keys = ["id"]
    replication_key = "updated_at"
    schema_filepath = SCHEMAS_DIR / "product.json"


class TransactionsStream(tap_shopifyStream):
    """Transactions stream."""

    parent_stream_type = OrdersStream

    name = "transactions"
    path = "/orders/{order_id}/transactions.json"
    records_jsonpath = "$.transactions[*]"
    primary_keys = ["id"]
    schema_filepath = SCHEMAS_DIR / "transaction.json"


class UsersStream(tap_shopifyStream):
    """Users stream."""

    name = "users"
    path = "/users.json"
    records_jsonpath = "$.users[*]"
    primary_keys = ["id"]
    schema_filepath = SCHEMAS_DIR / "user.json"
