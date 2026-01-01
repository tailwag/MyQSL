import os
from O365 import Account, FileSystemTokenBackend
import xml.etree.ElementTree as ET
from config import get_config


def load_o365_credentials(path="resource/config.xml"):
    client_id = get_config("O365/Credentials/ClientID")
    tenant_id = get_config("O365/Credentials/TenantID")
    client_secret = get_config("O365/Credentials/SecretValue")
    email = get_config("O365/Credentials/Email")

    return (client_id.strip(), client_secret.strip()), tenant_id.strip(), email.strip()


credentials, tenant_id, email = load_o365_credentials()
token_backend = FileSystemTokenBackend(token_path=".", token_filename="o365_token.txt")
account = Account(credentials, tenant_id=tenant_id, auth_flow_type='credentials', token_backend=token_backend)

if not account.is_authenticated:
    account.authenticate()


def sendMessage(to, subject, body, attachment):
    if not all([to, subject, body, attachment]):
        raise RuntimeError("Incomplete email data")

    if not os.path.isfile(attachment):
        raise RuntimeError("Attachment not found")

    if not account.is_authenticated:
        account.authenticate()

    try:
        mb = account.mailbox(resource=email)
        m = mb.new_message()
        m.to.add(to)
        m.subject = subject
        m.body = body
        m.attachments.add(attachment)
        m.send()
    except Exception as e:
        raise RuntimeError(e)
