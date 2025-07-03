class Pipe():

    def __init__(self):
        pass



if __name__ == "__main__":
    line = "a->[c->d->d|e->f]->[f->g]->h"
    ops = []
    for sub_line in line.split("["):
        for sub_line2 in sub_line.split("]"):
            ops.append(sub_line2)

    print(ops)