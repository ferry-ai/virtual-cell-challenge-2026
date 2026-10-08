"""Same Kaggle save operation, preserving the provider's useful error body."""
import sys
from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()
try:
    api.kernels_push_cli(sys.argv[1], None, None)
except Exception as exc:
    print(type(exc).__name__ + ': ' + str(exc))
    response = getattr(exc, 'response', None)
    if response is not None:
        print('Provider response: ' + response.text[:4000])
    sys.exit(1)
