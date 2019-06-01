class TapeIndices:
    START = 0
    FIRST_KNOWN_ZERO = START
    STOP_INDICATOR_INDEX = FIRST_KNOWN_ZERO + 1
    KNOWN_ZERO = STOP_INDICATOR_INDEX + 1
    END_STOP_INDICATOR = STOP_INDICATOR_INDEX + 1

    START_IP_WORKSPACE = KNOWN_ZERO + 1
    IP_INDEX = START_IP_WORKSPACE
    IP_ZERO_INDICATOR = IP_INDEX + 1
    END_IP_WORKSPACE = IP_ZERO_INDICATOR + 4

    START_STACK = END_IP_WORKSPACE + 1

    @classmethod
    def get_names(cls, index):
        m = cls.__dict__
        r = {v: [k for k in m if m[k] == v and type(v) == int] for v in m.values()}
        return r.get(index, [])
