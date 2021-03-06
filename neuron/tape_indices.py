class TapeIndices:
    START = 0
    FIRST_KNOWN_ZERO = START
    STOP_INDICATOR_INDEX = FIRST_KNOWN_ZERO + 1
    KNOWN_ZERO = STOP_INDICATOR_INDEX + 1
    END_STOP_INDICATOR = STOP_INDICATOR_INDEX + 1

    START_IP_WORKSPACE = KNOWN_ZERO + 1
    IP_INDEX = START_IP_WORKSPACE
    IP_ZERO_INDICATOR = IP_INDEX + 1
    IP_ZERO_QUERY_STOP = IP_ZERO_INDICATOR + 1
    IP_ZERO_QUERY_LANDING_1 = IP_ZERO_QUERY_STOP + 1
    IP_ZERO_QUERY_LANDING_2 = IP_ZERO_QUERY_LANDING_1 + 1
    IP_ZERO_QUERY_LANDING_3 = IP_ZERO_QUERY_LANDING_2 + 1
    END_IP_WORKSPACE = IP_ZERO_QUERY_LANDING_3

    START_STACK = END_IP_WORKSPACE + 1
    END_STACK = START_STACK + 15

    START_ADDRESSABLE_MEMORY = END_STACK + 1
    START_LVALUES = START_ADDRESSABLE_MEMORY
    LVALUES_COUNT = 10
    END_LVALUES = START_LVALUES + LVALUES_COUNT * 3 - 1

    START_STATIC_SEGMENT = END_LVALUES + 1

    @classmethod
    def get_names(cls, index):
        m = cls.__dict__
        r = {v: [k for k in m if m[k] == v and type(v) == int] for v in m.values()}
        return r.get(index, [])
