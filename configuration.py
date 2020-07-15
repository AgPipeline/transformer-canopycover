"""Contains transformer configuration information
"""
from agpypeline.configuration import Configuration


class ConfigurationCanopycover(Configuration):
    """Configuration information for Canopy Cover Transformer"""
    # Silence this error until we have public methods
    # pylint: disable=too-few-public-methods

    # The version number of the transformer
    transformer_version = '3.0'

    # The transformer description
    transformer_description = 'Canopy Cover by Plot (Percentage of Green Pixels)'

    # Short name of the transformer
    transformer_name = 'terra.stereo-rgb.canopycover'

    # The sensor associated with the transformer
    transformer_sensor = 'stereoTop'

    # The transformer type (eg: 'rgbmask', 'plotclipper')
    transformer_type = 'canopyCover'

    # The name of the author of the extractor
    author_name = 'Chris Schnaufer'

    # The email of the author of the extractor
    author_email = 'schnaufer@email.arizona.edu'

    # Contributors to this transformer
    CONTRIBUTORS = ["Zongyang Li"]

    # Repository URI of where the source code lives
    REPOSITORY = 'https://github.com/AgPipeline/transformer-canopycover.git'
