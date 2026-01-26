from regos.api import regos_api_request
from core.utils import write_json_file

response = regos_api_request(
    endpoint="DocumentType/Get",
    request_data={},
    token="af599525b17f4053912c86e3e1f36d28"
)
print(response)
write_json_file(response["result"], "document_types.json")