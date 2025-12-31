class DownstreamError(Exception):
    def __init__(self, service: str, code: str, detail: str = ""):
        super().__init__(f"{service}:{code}:{detail}")
        self.service = service
        self.code = code
        self.detail = detail
