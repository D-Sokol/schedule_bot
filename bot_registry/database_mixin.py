from sqlalchemy.ext.asyncio import AsyncSession


class DatabaseRegistryMixin:
    def __init__(self, session: AsyncSession, **kwargs):
        super().__init__(**kwargs)
        self.session = session
