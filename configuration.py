"""Contains transformer configuration information
"""

# The version number of the transformer
TRANSFORMER_VERSION = '3.0'

# The transformer description
TRANSFORMER_DESCRIPTION = 'Canopy Cover by Plot (Percentage of Green Pixels)'

# Short name of the transformer
TRANSFORMER_NAME = 'terra.stereo-rgb.canopycover'

# The sensor associated with the transformer
TRANSFORMER_SENSOR = 'stereoTop'

# The transformer type (eg: 'rgbmask', 'plotclipper')
TRANSFORMER_TYPE = 'canopyCover'

# The name of the author of the extractor
AUTHOR_NAME = 'Chris Schnaufer'

# The email of the author of the extractor
AUTHOR_EMAIL = 'schnaufer@email.arizona.edu'

# Contributors to this transformer
CONTRUBUTORS = ["Zongyang Li"]

# Reposity URI of where the source code lives
REPOSITORY = 'https://github.com/AgPipeline/transformer-canopycover.git'
