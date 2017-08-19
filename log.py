from time import strftime, localtime


class DB:
    def __init__(self):
        f_name = strftime("%Y_%m_%d_%H_%M_%S.csv", localtime())
        self.f = open(f_name, 'w+')

    def insert(self, data):
        self.f.write(','.join(str(x) for x in data) + '\n')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.f.close()


class Log:
    f = None
    def __init__(self):
        if Log.f is None:
            f_name = strftime("%Y_%m_%d_%H_%M_%S.log", localtime())
            Log.f = open(f_name, "w+")

    def __call__(self, data):
        print(t(), data)
        Log.f.write("{} {}\n".format(t(), data))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        Log.f.close()

def t():
    return strftime("%H:%M:%S", localtime())
