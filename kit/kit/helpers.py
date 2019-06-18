import builtins
import datetime
import logging
import re

from math import log2

first_cap_re = re.compile("(.)([A-Z][a-z]+)")
all_cap_re = re.compile("([a-z0-9])([A-Z])")

logger = logging.getLogger(__name__)

reserved_keywords = set(dir(builtins))


def to_python_name(prop_name):
    prop_name = to_snake_case(prop_name)

    prop_name = prop_name.replace("$", "_").replace("@", "_")

    if prop_name in reserved_keywords:
        prop_name = "_" + prop_name

    return prop_name


def parse_type(string: str) -> type:
    if string == "str":
        return str
    if string == "bool":
        return bool
    if string == "int":
        return int
    if string == "float":
        return float
    if string == "list":
        return list
    if string == "set":
        return set
    if string == "dict":
        return dict
    if string == "object":
        return object
    if string == "tuple":
        return tuple
    if string == "datetime":
        return datetime.datetime
    if string == "timedelta":
        return datetime.timedelta


def to_snake_case(string: str) -> str:
    s1 = first_cap_re.sub(r"\1_\2", string)
    return all_cap_re.sub(r"\1_\2", s1).lower()


def to_camel_case(string: str) -> str:
    first, *rest = string.split("_")
    return first + "".join(word.capitalize() for word in rest)


def get_azure_cli_auth_token(resource):
    from adal import AuthenticationContext
    import os

    try:
        # this makes it cleaner, but in case azure cli is not present on virtual env,
        # but cli exists on computer, we can try and manually get the token from the cache
        from azure.cli.core._profile import Profile
        from azure.cli.core._session import ACCOUNT
        from azure.cli.core._environment import get_config_dir

        azure_folder = get_config_dir()
        ACCOUNT.load(os.path.join(azure_folder, "azureProfile.json"))
        profile = Profile(storage=ACCOUNT)
        token_data = profile.get_raw_token()[0][2]

        client_id = token_data["_clientId"]
        refresh_token = token_data["refreshToken"]

        logger.info(f"Found existing AZ CLI profile for {token_data[0]['userId']}")

    except ModuleNotFoundError:
        try:
            import os
            import json

            folder = os.getenv("AZURE_CONFIG_DIR", None) or os.path.expanduser(os.path.join("~", ".azure"))
            token_path = os.path.join(folder, "accessTokens.json")
            with open(token_path) as f:
                data = json.load(f)

            client_id = data[0]["_clientId"]
            refresh_token = data[0]["refreshToken"]

            logger.info(f"Found existing AZ CLI profile for {data[0]['userId']}")
        except Exception:
            return None

    return AuthenticationContext(f"https://login.microsoftonline.com/common").acquire_token_with_refresh_token(
        refresh_token, client_id, f"https://{resource}.kusto.windows.net"
    )["accessToken"]


_suffixes = ["bytes", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]


def human_readable(size):
    # determine binary order in steps of size 10
    # (coerce to int, // still returns a float)
    order = int(log2(size) / 10) if size else 0
    # format file size
    # (.4g results in rounded numbers for exact matches and max 3 decimals,
    # should never resort to exponent values)
    return "{:.4g} {}".format(size / (1 << (order * 10)), _suffixes[order])
