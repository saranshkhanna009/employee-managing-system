"""Shared API route configuration."""

from fastapi.routing import APIRoute


class SnakeCaseAPIRoute(APIRoute):
    """Serialize response models using field names instead of aliases."""

    def __init__(self, *args, **kwargs):
        kwargs["response_model_by_alias"] = False
        super().__init__(*args, **kwargs)
