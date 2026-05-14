import traceback
import sys

try:
    import app.main
    print("Success")
except Exception as e:
    with open('err.txt', 'w') as f:
        traceback.print_exc(file=f)
    print("Failed - traceback written to err.txt")
