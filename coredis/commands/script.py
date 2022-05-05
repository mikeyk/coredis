from __future__ import annotations

import hashlib
from typing import cast

from coredis.exceptions import NoScriptError
from coredis.protocols import SupportsScript
from coredis.typing import (
    AnyStr,
    Generic,
    Iterable,
    KeyT,
    Optional,
    ResponseType,
    StringT,
    ValueT,
)
from coredis.utils import b


class Script(Generic[AnyStr]):
    """
    An executable Lua script object returned by :meth:`coredis.Redis.register_script`
    """

    sha: AnyStr

    def __init__(
        self,
        registered_client: SupportsScript[AnyStr],
        script: StringT,
    ):
        """
        :param script: The lua script that will be used by :meth:`execute`
        """
        self.registered_client: SupportsScript[AnyStr] = registered_client
        self.script = script
        self.sha = hashlib.sha1(b(script)).hexdigest()  # type: ignore

    async def execute(
        self,
        keys: Optional[Iterable[KeyT]] = None,
        args: Optional[Iterable[ValueT]] = None,
        client: Optional[SupportsScript[AnyStr]] = None,
    ) -> ResponseType:
        """
        Executes the script registered in :paramref:`Script.script`
        """
        from coredis.commands.pipeline import Pipeline

        if client is None:
            client = self.registered_client
        # make sure the Redis server knows about the script
        if isinstance(client, Pipeline):
            # make sure this script is good to go on pipeline
            cast(Pipeline[AnyStr], client).scripts.add(self)

        try:
            return cast(
                ResponseType, await client.evalsha(self.sha, keys=keys, args=args)
            )
        except NoScriptError:
            # Maybe the client is pointed to a different server than the client
            # that created this instance?
            # Overwrite the sha just in case there was a discrepancy.
            self.sha = cast(AnyStr, await client.script_load(self.script))
            return cast(
                ResponseType, await client.evalsha(self.sha, keys=keys, args=args)
            )
