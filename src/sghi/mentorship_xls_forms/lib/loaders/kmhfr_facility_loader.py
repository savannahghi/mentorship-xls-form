from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping, Sequence
from logging import Logger
from typing import Final, Self, TypedDict, override

from attrs import define, field, validators
from requests import PreparedRequest, Request, Response, Session
from requests.auth import AuthBase

from sghi.disposable import not_disposed
from sghi.mentorship_xls_forms.core import Facility, Loader
from sghi.utils import ensure_instance_of, type_fqn

# =============================================================================
# TYPES
# =============================================================================


type _ValidResPredicate = Callable[[Response], bool]


class _AuthResponse(TypedDict):
    access_token: str
    expires_in: int
    refresh_token: str
    scope: str
    token_type: str


class _FacilityEntryResponse(TypedDict):
    id: str
    officialname: str
    code: int
    county_name: str
    sub_county_name: str
    ward_name: str


class _ListFacilitiesResponse(TypedDict):
    count: int
    next: str | None
    previous: str | None
    page_size: int
    current_page: int
    total_pages: int
    start_index: int
    end_index: int
    results: Sequence[_FacilityEntryResponse]


# =============================================================================
# CONSTANTS
# =============================================================================


_COUNTY_KAJIADO_ID: Final[str] = "359719c8-25f3-49b3-8549-bd5fbb99f2c1"

_COUNTY_NAIROBI_ID: Final[str] = "95b08378-362e-4bf9-ad63-d685e1287db2"

_DEFAULT_CONNECT_TIMEOUT: Final[float] = 10.0

_DEFAULT_READ_TIMEOUT: Final[float] = 60.0

_KMHFL_PROD_API_URL: Final[str] = "https://api.kmhfr.health.go.ke"


# =============================================================================
# HELPERS
# =============================================================================


def _is_successful_res(res: Response) -> bool:
    ensure_instance_of(
        value=res,
        klass=Response,
        message=f"'res' MUST be a '{type_fqn(Response)}' instance.",
    )
    return 200 <= res.status_code < 400


# =============================================================================
# LOADER
# =============================================================================


@define
class KMHFRFacilityLoader(Loader[Iterable[Facility]]):
    _kmhfr_api_url: str = field(
        alias="kmhfr_api_url",
        default=_KMHFL_PROD_API_URL,
        validator=[validators.instance_of(str), validators.min_len(2)],
    )
    _username: str = field(
        alias="username",
        default="public@mfltest.slade360.co.ke",
        repr=False,
        validator=[validators.instance_of(str)],
    )
    _password: str = field(
        alias="password",
        default="public",
        repr=False,
        validator=[validators.instance_of(str)],
    )
    _oath_client_id: str = field(
        alias="oath_client_id",
        default="xMddOofHI0jOKboVxdoKAXWKpkEQAP0TuloGpfj5",
        repr=False,
        validator=[validators.instance_of(str), validators.min_len(3)],
    )
    _oath_client_secret: str = field(
        alias="oath_client_secret",
        default=(
            "PHrUzCRFm9558DGa6Fh1hEvSCh3C9Lijfq8s"
            "bCMZhZqmANYV5ZP04mUXGJdsrZLXuZG4VCmv"
            "jShdKHwU6IRmPQld5LDzvJoguEP8AAXGJhrq"
            "fLnmtFXU3x2FO1nWLxUx"
        ),
        repr=False,
        validator=[validators.instance_of(str), validators.min_len(3)],
    )
    _connect_timeout: float = field(
        alias="connect_timeout",
        default=_DEFAULT_CONNECT_TIMEOUT,
        repr=False,
        validator=[validators.instance_of(float), validators.ge(0)],
    )
    _read_timeout: float = field(
        alias="read_timeout",
        default=_DEFAULT_READ_TIMEOUT,
        repr=False,
        validator=[validators.instance_of(float), validators.ge(0)],
    )
    _logger: Logger = field(init=False, repr=False)
    _session: Session = field(factory=Session, init=False, repr=False)
    _timeout: tuple[float, float] = field(init=False, repr=False)
    _auth: AuthBase = field(init=False, repr=False)
    _is_disposed: bool = field(default=False, init=False, repr=False)

    def __attrs_post_init__(self) -> None:
        client_headers: dict[str, str] = {
            "Accept": "application/json",
            "ContentType": "application/json",
        }
        self._session.headers.update(client_headers)
        self._session.hooks["response"].append(self._log_response)
        self._logger = logging.getLogger(type_fqn(self.__class__))
        self._timeout = (self._connect_timeout, self._read_timeout)
        self._auth = _NoAuth()

    @property
    @override
    def is_disposed(self) -> bool:
        return self._is_disposed

    @override
    def dispose(self) -> None:
        self._is_disposed = True
        self._session.close()
        self._logger.info("Disposal complete.")

    @not_disposed
    @override
    def load(self) -> Iterable[Facility]:
        self._logger.info(
            "Loading facilities from the KMHFR instance at: %s.",
            self._kmhfr_api_url,
        )
        page: int = 1
        while True:
            facilities, has_next = self._load_facilities_on_page(page)
            yield from facilities
            if not has_next:
                break
            page += 1

    @classmethod
    def of_file_path(cls, _: str) -> Self:
        # This is needed to conform to the interface required by the
        # `sghi.use_cases.LoadMetadata` task.
        # The function is expected to take a file path of the metadata to
        # load.
        # This function does not need the given file path, so it is ignored.
        return cls()

    @not_disposed
    def _load_facilities_on_page(
        self,
        page: int,
    ) -> tuple[Iterable[Facility], bool]:
        # noinspection PyArgumentList
        res: Response = self._make_request(
            req=Request(
                method="GET",
                params={
                    "county": ",".join(
                        (_COUNTY_KAJIADO_ID, _COUNTY_NAIROBI_ID)
                    ),
                    "format": "json",
                    "page": str(page),
                    "page_size": "250",
                },
                # -> url=f"{self._kmhfr_api_url}/api/facilities/facilities/",
                url=f"{self._kmhfr_api_url}/api/facilities/material/",
            ),
        )
        res_content: _ListFacilitiesResponse = res.json()
        return (
            self._facility_list_res_to_objects(res_content["results"]),
            res_content["next"] is not None,
        )

    @not_disposed
    def _authenticate(self) -> AuthBase:
        res: Response = self._session.post(
            data={
                "client_id": self._oath_client_id,
                "client_secret": self._oath_client_secret,
                "grant_type": "password",
                "password": self._password,
                "username": self._username,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            url=f"{self._kmhfr_api_url}/o/token/",
        )
        if res.status_code != 200:
            _err_msg: str = (
                "Failed to authenticate. Expected status code 200 but got "
                f"status code {res.status_code} instead. Server says: "
                f"{res.text}."
            )
            raise RuntimeError(_err_msg)
        res_content: _AuthResponse = res.json()
        return _Authenticated(
            {"Authorization": f"Bearer {res_content['access_token']}"},
        )

    def _log_response(
        self,
        response: Response,
        *_,
        **__,
    ) -> None:  # pragma: no cover
        self._logger.info(
            "HTTP Request (%s | %s)",
            response.request.method,
            response.request.url,
        )

    @not_disposed
    def _make_request(
        self,
        req: Request,
        valid_res_predicate: _ValidResPredicate = _is_successful_res,
        remaining_retries: int = 3,
    ) -> Response:
        ensure_instance_of(
            value=req,
            klass=Request,
            message=f"'req' Must be a '{type_fqn(Request)}' instance.",
        )
        res: Response = self._session.request(
            auth=self._auth,
            data=req.data,
            headers=req.headers,
            json=req.json,
            method=req.method,
            params=req.params,
            timeout=self._timeout,
            url=req.url,
        )

        unauthenticated_status_codes: set[int] = {
            401,
            403,
            # Why 500?
            # Currently, there is a bug with KMHFR where it runs a response
            # with status code 500 when the request is unauthenticated.
            500,
        }
        if (
            res.status_code in unauthenticated_status_codes
            and remaining_retries >= 0
        ):
            # Authenticate and then retry the response.
            # noinspection PyArgumentList
            self._auth = self._authenticate()
            # noinspection PyArgumentList
            return self._make_request(
                req=req,
                valid_res_predicate=valid_res_predicate,
                remaining_retries=remaining_retries - 1,
            )

        if (
            res.status_code in unauthenticated_status_codes
            and remaining_retries < 0
        ):
            _err_msg: str = "Authentication loop detected. Exiting."
            raise RuntimeError(_err_msg)

        if not valid_res_predicate(res):
            _err_msg: str = (
                "Server returned an invalid response. Server says: "
                f"{res.text}."
            )
            raise RuntimeError(_err_msg)

        return res

    @staticmethod
    def _facility_list_res_to_objects(
        facilities: Iterable[_FacilityEntryResponse],
    ) -> Iterable[Facility]:
        yield from (
            Facility(
                name=facility_res["officialname"],
                county=facility_res["county_name"],
                sub_county=facility_res["sub_county_name"],
                mfl_code=str(facility_res["code"]),
                ward=facility_res["ward_name"],
            )
            for facility_res in facilities
            if facility_res["code"] is not None
        )


# =============================================================================
# HTTP TRANSPORT AUTH
# =============================================================================


class _Authenticated(AuthBase):
    """
    The ``Auth`` implementation used by the :class:`KMHFRFacilityLoader`
    after a successful authentication.
    """

    def __init__(self, auth_headers: Mapping[str, str]):
        super().__init__()
        self._auth_headers = auth_headers

    def __call__(
        self,
        r: PreparedRequest,
        *args,
        **kwargs,
    ) -> PreparedRequest:  # pragma: no cover
        r.headers.update(self._auth_headers)
        return r


class _NoAuth(AuthBase):
    """
    An ``Auth`` implementation of an un-authenticated
    :class:`KMHFRFacilityLoader`.
    """

    def __call__(
        self,
        r: PreparedRequest,
        *args,
        **kwargs,
    ) -> PreparedRequest:  # pragma: no cover
        return r
