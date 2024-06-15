#!/usr/bin/env python3
import sys
from xyzzy import Xyzzy


#print(sys.argv)

# TODO read story file from args
def main():
    state = Xyzzy()
    for argv in sys.argv[1:]:
        state.read(argv)
    state.run()


if __name__ == "__main__":
    main()
