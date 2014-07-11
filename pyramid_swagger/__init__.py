"""
Import this module to add the validation tween to your pyramid app.
"""
import pyramid
from .api import register_swagger_endpoints


def includeme(config):
    config.add_tween(
        "pyramid_swagger.tween.validation_tween_factory",
        under=pyramid.tweens.EXCVIEW
    )
    register_swagger_endpoints(config)
