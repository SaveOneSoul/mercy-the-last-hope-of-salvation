"""Manual delivery worker entrypoint.

Usage (only after operator-approved Meta onboarding):
  python -m app.whatsapp_worker_cli

Never schedule this command until the security/acceptance gate is passed.
"""
from .whatsapp_worker import dispatch_one

if __name__ == "__main__":
    print(dispatch_one())
