import asyncio
from typing import List, Optional, Any

from core.utils import convert_to_unix_timestamp
from regos.api import regos_async_api_request


class RegosReports:
    def __init__(self):
        pass

    def create_endpoint_from_operation_type(self, operation_type: str) -> tuple:
        if operation_type == "purchase":
            return "DocPurchase/Get", "PurchaseOperation/Get"
        elif operation_type == "wholesale":
            return "DocWholeSale/Get", "WholesaleOperation/Get"
        elif operation_type == "return_to_partner":
            return "DocReturnsToPartner/Get", "ReturnsToPartnerOperation/Get"
        else:
            return "DocWholeSaleReturn/Get", "WholeSaleReturnOperation/Get"

    async def partner_balance_report(self, token: str, partner_id: int, firm_id: int, start_time: str, end_time: str) -> dict:
        timestamp_start_time = convert_to_unix_timestamp(start_time)
        timestamp_end_time = convert_to_unix_timestamp(end_time)

        request_data = {
            "start_date": timestamp_start_time,
            "end_date": timestamp_end_time,
            "partner_id": partner_id,
            "firm_id": firm_id
        }
        partner_balance_data = await regos_async_api_request(
            request_data=request_data,
            endpoint="PartnerBalance/Get",
            token=token
        )

        return partner_balance_data

    async def get_partner_stock_operations(self, token: str, partner_id: int, start_time: str, end_time: str,
                                           operation_type: str, stock_ids: List[int] | None = None,
                                           firm_ids: List[int] | None = None,) -> dict:
        timestamp_start_time = convert_to_unix_timestamp(start_time)
        timestamp_end_time = convert_to_unix_timestamp(end_time)

        document_endpoint, operation_endpoint = self.create_endpoint_from_operation_type(operation_type)

        request_data = {
            "start_date": timestamp_start_time,
            "end_date": timestamp_end_time,
            "partner_ids": [partner_id, ],
            "performed": True
        }

        if firm_ids: request_data["firm_ids"] = firm_ids
        if stock_ids: request_data["stock_ids"] = stock_ids

        docs = await regos_async_api_request(
            token=token,
            endpoint=document_endpoint,
            request_data=request_data
        )

        if not docs or not docs.get("ok") or len(docs.get("result", [])) == 0:
            return {}

        doc_ids = [doc["id"] for doc in docs["result"]]

        operations = await regos_async_api_request(
            token=token,
            endpoint=operation_endpoint,
            request_data={
                "document_ids": doc_ids
            }
        )

        if not operations or not operations.get("ok") or len(operations.get("result", [])) == 0:
            return {}

        return {
            f"documents": docs["result"],
            f"operations": operations["result"]
        }

    async def get_partner_payments(
            self,
            token: str,
            partner_id: int,
            start_time: str,
            end_time: str,
            firm_ids: Optional[List[int]] = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Fetch partner income and outcome payments from REGOS within a given date range."""

        timestamp_start_time = convert_to_unix_timestamp(start_time)
        timestamp_end_time = convert_to_unix_timestamp(end_time)

        base_request = {
            "start_date": timestamp_start_time,
            "end_date": timestamp_end_time,
            "partner_ids": [partner_id],
            "performed": True,
        }
        if firm_ids:
            base_request["firm_ids"] = firm_ids

        # Prepare parallel requests
        request_income = {**base_request, "payment_direction": "Income"}
        request_outcome = {**base_request, "payment_direction": "Outcome"}

        income_task = regos_async_api_request(token=token, endpoint="DocPayment/Get", request_data=request_income)
        outcome_task = regos_async_api_request(token=token, endpoint="DocPayment/Get", request_data=request_outcome)

        income_payments, outcome_payments = await asyncio.gather(income_task, outcome_task)

        result = {}
        if income_payments and income_payments.get("ok") and income_payments.get("result"):
            result["income"] = income_payments["result"]
        if outcome_payments and outcome_payments.get("ok") and outcome_payments.get("result"):
            result["outcome"] = outcome_payments["result"]

        return result




