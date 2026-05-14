import sys
try:
    import transformers.modeling_utils
    from transformers import PreTrainedModel
except Exception as e:
    import traceback
    traceback.print_exc()
