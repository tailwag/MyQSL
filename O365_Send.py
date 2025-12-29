import os
from O365 import Account
import xml.etree.ElementTree as ET


def load_o365_credentials(path="config/O365_config.xml"):
    tree = ET.parse(path)
    root = tree.getroot()

    creds = root.find("Credentials")
    if creds is None:
        raise RuntimeError("Missing <Credentials> block")

    client_id = creds.findtext("client_id")
    client_secret = creds.findtext("client_secret_value")
    tenant_id = creds.findtext("tenant_id")
    email = creds.findtext("email")
    replyto = creds.findtext("replyto")

    if not client_id or not client_secret:
        raise RuntimeError("O365 credentials incomplete")

    return (client_id.strip(), client_secret.strip()), tenant_id.strip(), email.strip()


credentials, tenant_id, email = load_o365_credentials()
account = Account(credentials, tenant_id=tenant_id, auth_flow_type='credentials')

if not account.is_authenticated:
    account.authenticate()


def sendMessage(to, subject, body, attachment):
    if not all([to, subject, body, attachment]):
        raise RuntimeError("Incomplete email data")

    if not os.path.isfile(attachment):
        raise RuntimeError("Attachment not found")

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
