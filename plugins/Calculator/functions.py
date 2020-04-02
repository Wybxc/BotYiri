import random

class CalculateError(Exception):
    def __init__(self, msg):
        super(CalculateError, self).__init__()
        self.err_msg = msg


def iint(n, minimal=1):
    if isinstance(n, float):
        n = int(n)
    if n <= minimal or not isinstance(n, int):
        n = minimal
    return n

def ifloat(x, minimal=0.0):
    if isinstance(x, int):
        x = float(x)
    if not isinstance(x, float) or x < minimal:
        x = minimal
    return x

def dice(n):
    n = iint(n)
    return random.randint(1, n)

def dicem(count, n):
    result = 0
    if count > 100:
        raise CalculateError('数量过大！')
    for _ in range(iint(count)):
        result += dice(n)
    return result

def dicemf(count, n):
    if count > 100:
        raise CalculateError('数量过大！')
    dices = [dice(n) for _ in range(iint(count))]
    return f"{'+'.join([str(i) for i in dices])}={sum(dices)}"

def rand(*args):
    if len(args) == 0:
        return 0
    elif len(args) == 1:
        return random.random() * ifloat(args[0])
    else:
        x = ifloat(args[0])
        y = ifloat(args[1])
        return random.random() * (y - x) + x

def randn(mu=0.5, sigma=0.5):
    mu = ifloat(mu)
    sigma = ifloat(sigma)
    return random.normalvariate(mu, sigma)

builtins = {
    'dice': dice, 
    'd': dice,
    'dicem': dicem,
    'dm': dicem,
    'dicemf': dicemf,
    'dmf': dicemf,
    'rand': rand,
    'r': rand,
    'randn': randn,
    'rn': randn
}    