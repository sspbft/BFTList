"""Client shell to send requests to all BFTList nodes."""

from comm import build_payload, broadcast

APPEND = "append"
PREPEND = "prepend"

ops = [APPEND, PREPEND]

if __name__ == '__main__':
    print("Welcome to BFT Client shell! Available operations are \
[append x] and [prepend x]")
    while True:
        s = input("BFTList Client > ")
        parts = s.split(" ")
        if len(parts) != 2:
            print("Missing value for operation")
            continue
        op = parts[0]
        if op not in ops:
            print(f"Illegal operation {op}")
            continue
        val = int(parts[1])
        payload = build_payload(op, val)
        broadcast(payload)
