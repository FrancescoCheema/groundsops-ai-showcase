"""Create a company workspace and print a one-time invitation link for its owner.

Run on the server, for example to create your own operator workspace on a fresh production
database (sign-up is invite-only, so nobody can sign in until a workspace exists):

    docker compose --env-file .env.production -f docker-compose.staging.yml exec -T api \\
        python scripts/create-workspace.py --name "GroundsOps" --owner-email you@example.com
"""

import argparse
import sys

from groundsops.config import get_settings
from groundsops.db import SessionLocal
from groundsops.workspaces import EmailAlreadyInWorkspace, create_workspace_with_owner_invite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--name", required=True, help="Company name")
    parser.add_argument("--owner-email", required=True, help="Email the owner will sign in with")
    parser.add_argument("--expires-in-days", type=int, default=14, choices=range(1, 31))
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        try:
            organization, invitation, token = create_workspace_with_owner_invite(
                db,
                organization_name=args.name,
                owner_email=args.owner_email,
                expires_in_days=args.expires_in_days,
            )
        except EmailAlreadyInWorkspace:
            print(f"{args.owner_email} already belongs to a workspace.", file=sys.stderr)
            return 1
    base_url = get_settings().app_public_url.rstrip("/")
    print(f"Created workspace '{organization.name}' ({organization.id}).")
    print(f"Owner invitation for {invitation.email}, valid {args.expires_in_days} days:")
    print(f"{base_url}/?invite={token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
