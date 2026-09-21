import math

def require(condition,message):
    if not condition:raise ValueError(message)

def close(a,b,rtol=1e-10,atol=1e-6):
    return math.isclose(a,b,rel_tol=rtol,abs_tol=atol)
