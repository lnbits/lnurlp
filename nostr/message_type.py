class ClientMessageType:
    EVENT = "EVENT"
    REQUEST = "REQ"
    CLOSE = "CLOSE"


class RelayMessageType:
    EVENT = "EVENT"
    NOTICE = "NOTICE"
    END_OF_STORED_EVENTS = "EOSE"

    @staticmethod
    def is_valid(relay_type: str) -> bool:
        if (
            relay_type == RelayMessageType.EVENT
            or relay_type == RelayMessageType.NOTICE
            or relay_type == RelayMessageType.END_OF_STORED_EVENTS
        ):
            return True
        return False
