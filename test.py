from regos.api import regos_async_api_request
from core.utils import write_json_file
import asyncio

TEST_INTEGRATION_TOKEN = "986306b8a4854f0da12ca56a3a0f10a8"

# request_data = {
#     "filters": [{
#         "field": "oked",
#         "operator": "Like",
#         "value": "5391703573"
#     }]
# }

# result = asyncio.run(
#     regos_async_api_request(
#         endpoint="Partner/Get",
#         token=TEST_INTEGRATION_TOKEN,
#         request_data=request_data
#     ))



# print(result)
# write_json_file(result)

# Edit partner
request_data = {
    "id": 12,
    "field_rpb_telegram_id": "320423040234"
}

result = asyncio.run(
    regos_async_api_request(
        endpoint="Partner/Edit",
        token=TEST_INTEGRATION_TOKEN,
        request_data=request_data
    ))



# print(result)
# write_json_file(result)


# Create new fields
# request_data = {
#     "key": "rpb_telegram_id",
#     "name": "Телерам ID для RegosPartnerBot",
#     "entity_type": "Partner",
#     "data_type": "string",
#     "required": False
# }

# result = asyncio.run(
#     regos_async_api_request(
#         endpoint="Field/Get",
#         token=TEST_INTEGRATION_TOKEN,
#         request_data=request_data
#     ))

# print(result)
# write_json_file(result)