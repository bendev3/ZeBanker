LOGLEVEL = 1

def log(msg, level=0):
    if level <= LOGLEVEL:
        print(msg)

def val_to_float(val):
    return 0 if val == '' else float(val)
