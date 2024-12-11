from nats.js.client import JetStreamContext


class NATSRegistryMixin:
    def __init__(self, js: JetStreamContext, **kwargs):
        super().__init__(**kwargs)
        self.js = js
