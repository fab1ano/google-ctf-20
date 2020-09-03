tracing
=======

This was a challenge in Google CTF 2020.
I played the CTF with [Shellphish](https://ctftime.org/team/285).

Category: `pwn`, tagged as *easy*.

Description:
```
An early prototype of a contact tracing database is deployed for the developers to test, but is configured with some sensitive data. See if you can extract it.

tracing.2020.ctfcompetition.com 1337
```

Points: 151pt

The source code was provided (see [zip file](./source.zip)).


## Overview
Taking a look at the description of the challenge gives us a hint that maybe the goal is not to get remote code execution but rather to leak some information from the service.

Taking a look at the provided files tells us that this is a rust service.
```bash
$ tree
.
├── Cargo.toml
└── src
    ├── bin
    │   └── server.rs
    ├── bst.rs
    └── lib.rs

2 directories, 4 files
```

The file `Cargo.toml` defines the required dependencies and we can simply start the application using cargo:
```bash
$ RUST_LOG=debug cargo run <parameter>
```

The source files in [this repository](https://github.com/fab1ano/google-ctf-20/tree/master/tracing) contain additional debug output and comments in the source code, but do not affect the challenge.
The original source files are available in [`source.zip`](./source.zip).

Looking at `server.rs` we can see, that the binary runs a server and listens on port 1337 (`const BIND_ADDR: &str = "0.0.0.0:1337";`).
Incoming connections are then handled by the function `accept`.
It reads UUIDs from the client until the client closes the connection.
The UUIDs from the client are stored in a Binary Search Tree (BST) called `tree` which is unique for each client.
Before shutting down the connection to the client the server searches for every UUID in `tree` that has been provided as a command line parameter to the binary.
I.e., if we start the the binary with `RUST_LOG=debug cargo run AAAAAAAAAAAAAAAA`, it will search for the value `AAAAAAAAAAAAAAAA` in the binary search tree `tree` after our values have been inserted.

This provides us a timing side-channel.
We can measure the time difference of the search happening on the server between closing the client-side connection (after sending the last UUID) and waiting for the server to close the connection.

Given the description of the challenge, we can assume that the only command line parameter for the binary is probably the flag we are looking for.


## Approach
Though, how do we utilize the side-channel to extract the value that the server searches for in the BST `tree`?
We need to insert values in the BST such that the duration of the search gives us information about the desired value.
Since the BST is sorted, we can use that characteristic.
Also, the `tree` never is rebalanced (see `find_slot` in [bst.rs](src/bst.rs)).

Therefore, if we provide all UUIDs in either ascending or descending order, the BST effectively becomes a sorted list:

```
     +-------------+
     |    tree     |
     +-------------+
            |
            v
        +-------+
        |  100  |
        +-------+
            |
    +-------+-------+
    v               v
                +-------+
                |  101  |
                +-------+
                    |
            +-------+-------+
            v               v
                        +-------+
                        |  102  |
                        +-------+
                            |
                    +-------+-------+
                    v               v
                                +-------+
                                |  103  |
                                +-------+
                                    |
                            +-------+-------+
                            v               v
                                           ... 
```

Thus, during the search for a value `v` in the tree the number of traversed nodes depends on the value of `v`.
In the example tree provided above, for `v == 5` only the root node needs to be accessed to determine whether `v` is in the tree.
Whereas, when `v` is larger than all values in `tree` all nodes in `tree` need to be accessed to verify that `v` is not in the tree.

Given this knowledge, we can send the server a large number (i.e. 10.000) of consecutive UUIDs, and depending on the search duration we can guess whether the flag is smaller or larger than our values.
With this technique, we can use a binary search and leak 1 Bit At A Time.


## Exploit
You can find the full exploit in [x.py](./x.py).

I have created a function `exploit` which receives an open connection, sends a large number of UUIDs, and returns the duration of the search.
We can now loop over the `exploit` function (see function `loop`) to leak each bit of the flag.
The `loop` function provides either a manual mode where one can modify the current guessed value of the flag after each iteration.
Also, in the auto mode (for remote), the current assumed value of the flag is extended/modified automatically based on thresholds (`THRESHOLD_*`).

The execution of the exploit script in manual mode looks like this:
```bash
$ ./x.py local
[*] Trying to connect ..
[+] Opening connection to localhost on port 1337: Done
[*] Current value: b'CTF{1Bit\xff\xff\xff\xff\xff\xff'
[*] In binary representation: 01000011 01010100 01000110 01111011 00110001 01000010 01101001 01110100
[*] Waiting for data transmission
[*] Shutting down socket in one direction
[+] Receiving all data: Done (4B)
[*] Closed connection to localhost port 1337
[*] time: 0.006028652191162109
[*] Current value: b'CTF{1Bit\xff\xff\xff\xff\xff\xff'
[*] In binary representation: 01000011 01010100 01000110 01111011 00110001 01000010 01101001 01110100
[*] Your Choice? Add '1', add '0', 'r'emove a bit, or 'n'one:

```

With the right threshold values and the right number of UUIDs sent each iteration (see `UUID_COUNT`), we can reliably leak one bit in each iteration (even without a VPS).
Only the last two bytes cannot be leaked with this exploit, since there are not enough bits to reliably use the side-channel.
However, since we got most of the flag, we can guess the two remaining bytes.


## Note
You may have wondered why we set the `RUST_LOG=debug` for the server.
If the log level does not include the debug level, the following debug output in the BST search is not triggered:
```
debug!("Stepping through {:?}", inner.v);
```
However, the output of that string for every node is necessary for the reliable timing side-channel.
I have done measurements on my local machine with both the debug output enabled and disabled.
Without the debug output, I was not able to get a significant time difference for the side-channel attack.


## Flag
The extracted flag is `CTF{1BitAtATime}`.


## Conclusion
It was a nice simple beginner's challenge.
I didn't implement a lot of timing side-channel attacks before, and I am not a rust expert (yet).
However, the challenge was fun and a good warm-up.
