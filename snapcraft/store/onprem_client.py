import os
from typing import Any, Dict, Final

from craft_store import BaseClient, endpoints, models
from overrides import overrides

from snapcraft import errors
from . import constants

ON_PREM_ENDPOINTS: Final = endpoints.Endpoints(
    namespace="snap",
    whoami="/v1/tokens/whoami",
    tokens="",
    tokens_exchange="/v1/tokens/offline/exchange",
    valid_package_types=["snap"],
    list_releases_model=models.charm_list_releases_model.ListReleasesModel,
)


class OnPremClient(BaseClient):
    @overrides
    def _get_macaroon(self, token_request: Dict[str, Any]) -> str:
        macaroon_env = os.getenv(constants.ENVIRONMENT_ADMIN_MACAROON)
        if macaroon_env is None:
            raise errors.SnapcraftError(
                f"{constants.ENVIRONMENT_ADMIN_MACAROON!r} needs to be setup with a valid macaroon"
            )
        return macaroon_env

    @overrides
    def _get_discharged_macaroon(self, root_macaroon: str, **kwargs) -> str:
        response = self.http_client.request(
            "POST",
            self._base_url + self._endpoints.tokens_exchange,
            json={"macaroon": root_macaroon},
        )

        return response.json()["macaroon"]

    @overrides
    def _get_authorization_header(self) -> str:
        auth = self._auth.get_credentials()
        return f"macaroon {auth}"
